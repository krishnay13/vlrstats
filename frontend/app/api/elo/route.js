// frontend/app/api/elo/route.js

import { NextResponse } from 'next/server'
import db from '@/app/lib/db.js'
import { getTeamLogoUrl } from '@/app/lib/logos.js'
import { getMatchesDateMeta, getMatchDateExpr, getMatchDateNonEmptyWhere } from '@/app/lib/db/schema.js'
import { normalizeTeamName } from '@/app/lib/team-utils.js'

// Check if a table exists in the database
function tableExists(db, tableName) {
  try {
    const result = db.prepare(
      `SELECT name FROM sqlite_master WHERE type='table' AND name=?`
    ).get(tableName)
    return result !== undefined
  } catch (e) {
    return false
  }
}

// Parse date range string into start and end dates
function parseDateRange(dateRange) {
  if (!dateRange || dateRange.toLowerCase() === 'all-time') {
    return { startDate: null, endDate: null }
  }

  if (dateRange === '2024') {
    return { startDate: '2024-01-01', endDate: '2024-12-31' }
  } else if (dateRange === '2025') {
    return { startDate: '2025-01-01', endDate: '2025-12-31' }
  } else if (dateRange === '2026') {
    return { startDate: '2026-01-01', endDate: '2026-12-31' }
  }

  return { startDate: null, endDate: null }
}

// Get importance multiplier for a match
function getImportance(tournament, stage, matchType) {
  const t = (tournament || '').toLowerCase()
  const m = (matchType || '').toLowerCase()

  // Tournament category
  let tWeight = 1.0
  if (t.includes('champions')) {
    tWeight = 2.0
  } else if (t.includes('masters')) {
    tWeight = 1.8
  } else if (t.includes('kickoff') || t.includes('stage 1') || t.includes('stage 2')) {
    tWeight = 1.0
  }

  // Match type weighting
  let mWeight = 1.0
  if (m.includes('grand final')) {
    mWeight = 1.45
  } else if (m.includes('lower final') || m.includes('upper final')) {
    mWeight = 1.35
  } else if (m.includes('semifinal') || m.includes('semi-final')) {
    mWeight = 1.30
  } else if (m.includes('quarterfinal') || m.includes('quarter-final')) {
    mWeight = 1.25
  } else if (m.includes('playoffs')) {
    mWeight = 1.15
  }

  return tWeight * mWeight
}

// Margin of victory multiplier
function movMultiplier(margin, rdiff) {
  return Math.log(1 + Math.max(1, margin)) * 2.2 / (Math.abs(rdiff) * 0.001 + 2.2)
}

// Expected score calculation
function expectedScore(rA, rB) {
  return 1.0 / (1.0 + Math.pow(10.0, (rB - rA) / 400.0))
}

// Compute Elo ratings from matches in a date range
function computeEloRatings(db, startDate, endDate, topN) {
  const dateMeta = getMatchesDateMeta(db)
  const dateExpr = getMatchDateExpr(dateMeta)
  const nonEmptyWhere = getMatchDateNonEmptyWhere(dateMeta)

  // Build query with date filtering
  let query = `
    SELECT match_id, tournament, stage, match_type, team_a, team_b, team_a_score, team_b_score
    FROM Matches
    WHERE team_a IS NOT NULL AND team_b IS NOT NULL
  `
  const params = []

  if (startDate || endDate) {
    if (dateExpr && nonEmptyWhere) {
      query += ` AND ${nonEmptyWhere}`
      if (startDate) {
        query += ` AND ${dateExpr} >= ?`
        params.push(startDate)
      }
      if (endDate) {
        query += ` AND ${dateExpr} <= ?`
        params.push(endDate)
      }
    }
  }

  query += ` ORDER BY ${dateExpr || 'match_id'} ASC`

  const matches = db.prepare(query).all(...params)

  // Elo computation with importance and margin of victory
  const START_ELO = 1500.0
  const K_BASE = 32.0
  const ratings = new Map()
  const gamesPlayed = new Map()

  for (const match of matches) {
    const teamA = normalizeTeamName(match.team_a)
    const teamB = normalizeTeamName(match.team_b)

    if (!teamA || !teamB) continue

    const ratingA = ratings.get(teamA) || START_ELO
    const ratingB = ratings.get(teamB) || START_ELO

    // Expected scores
    const expectedA = expectedScore(ratingA, ratingB)
    const expectedB = 1.0 - expectedA

    // Actual scores
    let actualA = 0.5
    let actualB = 0.5
    let margin = 0

    if (match.team_a_score !== null && match.team_b_score !== null) {
      if (match.team_a_score > match.team_b_score) {
        actualA = 1.0
        actualB = 0.0
        margin = match.team_a_score - match.team_b_score
      } else if (match.team_b_score > match.team_a_score) {
        actualA = 0.0
        actualB = 1.0
        margin = match.team_b_score - match.team_a_score
      }
    }

    // Calculate K with importance and margin of victory
    const importance = getImportance(match.tournament, match.stage, match.match_type)
    const rdiff = ratingA - ratingB
    const movMult = movMultiplier(margin, rdiff)
    const kEff = K_BASE * importance * movMult

    // Update ratings
    const newRatingA = ratingA + kEff * (actualA - expectedA)
    const newRatingB = ratingB + kEff * (actualB - expectedB)

    ratings.set(teamA, newRatingA)
    ratings.set(teamB, newRatingB)
    gamesPlayed.set(teamA, (gamesPlayed.get(teamA) || 0) + 1)
    gamesPlayed.set(teamB, (gamesPlayed.get(teamB) || 0) + 1)
  }

  // Convert to array and sort
  const results = Array.from(ratings.entries())
    .map(([team, rating]) => ({
      team,
      rating,
      matches: gamesPlayed.get(team) || 0
    }))
    .sort((a, b) => b.rating - a.rating)
    .slice(0, topN)

  return results
}

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url)
    const topTeams = Number(searchParams.get('topTeams') || 6)
    const topPlayers = Number(searchParams.get('topPlayers') || 6)
    const dateRange = searchParams.get('dateRange') || 'all-time'

    const { startDate, endDate } = parseDateRange(dateRange)
    const useDateRange = startDate !== null || endDate !== null

    let teams = []
    let players = []

    if (useDateRange) {
      // Compute Elo on-the-fly for 2026 (current year) and all-time
      if (dateRange === '2026') {
        teams = computeEloRatings(db, startDate, endDate, topTeams)
          .map((team) => ({
            ...team,
            logo_url: getTeamLogoUrl(team.team, 'small'),
          }))
      } else {
        // For 2024 and 2025, use pre-computed stored tables
        const tableName = `Elo_${dateRange}`
        if (tableExists(db, tableName)) {
          try {
            teams = db
              .prepare(
                `
                SELECT team, rating, matches
                FROM ${tableName}
                ORDER BY rating DESC
                LIMIT ?
                `
              )
              .all(topTeams)
              .map((team) => ({
                ...team,
                logo_url: getTeamLogoUrl(team.team, 'small'),
              }))
          } catch (error) {
            teams = []
          }
        }
      }

      // Get players from the corresponding table
      const playerTableName = dateRange === '2026' ? 'Player_Elo_Current' : `Player_Elo_${dateRange}`
      if (tableExists(db, playerTableName)) {
        try {
          players = db
            .prepare(
              `
              SELECT player, team, rating, matches
              FROM ${playerTableName}
              ORDER BY rating DESC
              LIMIT ?
              `
            )
            .all(topPlayers)
            .map((player) => ({
              ...player,
              team_logo: getTeamLogoUrl(player.team, 'small'),
            }))
        } catch (error) {
          players = []
        }
      }
    } else {
      // Use pre-computed Elo_Current table
      if (tableExists(db, 'Elo_Current')) {
        try {
          teams = db
            .prepare(
              `
              SELECT team, rating, matches
              FROM Elo_Current
              ORDER BY rating DESC
              LIMIT ?
              `
            )
            .all(topTeams)
            .map((team) => ({
              ...team,
              logo_url: getTeamLogoUrl(team.team, 'small'),
            }))
        } catch (error) {
          // Elo_Current table query failed, ignore
          teams = []
        }
      } else {
        // Elo_Current table does not exist yet
      }

      // Check if Player_Elo_Current table exists
      if (tableExists(db, 'Player_Elo_Current')) {
        try {
          players = db
            .prepare(
              `
              SELECT player, team, rating, matches
              FROM Player_Elo_Current
              ORDER BY rating DESC
              LIMIT ?
              `
            )
            .all(topPlayers)
            .map((player) => ({
              ...player,
              team_logo: getTeamLogoUrl(player.team, 'small'),
            }))
        } catch (error) {
          // Player_Elo_Current table query failed, ignore
          players = []
        }
      } else {
        // Player_Elo_Current table does not exist yet
      }
    }

    return NextResponse.json({ teams, players })
  } catch (error) {
    console.error('Error fetching Elo data:', error)
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
  }
}
