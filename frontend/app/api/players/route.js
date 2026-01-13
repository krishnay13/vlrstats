// frontend/app/api/players/route.js

import { NextResponse } from 'next/server';
import db from '@/app/lib/db.js';
import { isOlderThanSixMonths } from '@/app/lib/region-utils.js';
import { isShowmatchTeam, normalizeTeamName } from '@/app/lib/team-utils.js';

// Get player's last match date
function getPlayerLastMatchDate(db, playerName) {
  try {
    const tableInfo = db.prepare("PRAGMA table_info(Matches)").all();
    const columns = tableInfo.map(col => col.name);
    const hasMatchDate = columns.includes('match_date');
    const hasMatchTsUtc = columns.includes('match_ts_utc');
    
    // Get player's team from Player_Stats
    const playerTeam = db.prepare('SELECT DISTINCT team FROM Player_Stats WHERE player = ? LIMIT 1').get(playerName);
    if (!playerTeam || !playerTeam.team) return null;
    
    // Then find matches where that team played
    let result;
    if (hasMatchDate && hasMatchTsUtc) {
      result = db.prepare(`
        SELECT MAX(COALESCE(match_date, substr(match_ts_utc, 1, 10))) as last_match_date
        FROM Matches m
        WHERE (m.team_a = ? OR m.team_b = ?)
        AND ((match_date IS NOT NULL AND match_date != '') OR (match_ts_utc IS NOT NULL AND match_ts_utc != ''))
      `).get(playerTeam.team, playerTeam.team);
    } else if (hasMatchTsUtc) {
      result = db.prepare(`
        SELECT MAX(match_ts_utc) as last_match_date
        FROM Matches m
        WHERE (m.team_a = ? OR m.team_b = ?)
        AND match_ts_utc IS NOT NULL AND match_ts_utc != ''
      `).get(playerTeam.team, playerTeam.team);
    } else if (hasMatchDate) {
      result = db.prepare(`
        SELECT MAX(match_date) as last_match_date
        FROM Matches m
        WHERE (m.team_a = ? OR m.team_b = ?)
        AND match_date IS NOT NULL AND match_date != ''
      `).get(playerTeam.team, playerTeam.team);
    } else {
      return null;
    }
    
    return result?.last_match_date || null;
  } catch (e) {
    // Alternative: check Player_Stats -> Maps -> Matches directly
    try {
      const result = db.prepare(`
        SELECT MAX(COALESCE(m.match_date, substr(m.match_ts_utc, 1, 10))) as last_match_date
        FROM Player_Stats ps
        JOIN Maps mp ON ps.map_id = mp.id
        JOIN Matches m ON mp.match_id = m.match_id
        WHERE ps.player = ?
        AND ((m.match_date IS NOT NULL AND m.match_date != '') OR (m.match_ts_utc IS NOT NULL AND m.match_ts_utc != ''))
      `).get(playerName);
      
      return result?.last_match_date || null;
    } catch (e2) {
      return null;
    }
  }
}

// Get all teams a player has played for (for backend storage)
function getPlayerTeams(db, playerName) {
  try {
    const teams = db.prepare(`
      SELECT DISTINCT 
        ps.team as team_name,
        MAX(COALESCE(m.match_date, substr(m.match_ts_utc, 1, 10))) as last_match_date
      FROM Player_Stats ps
      LEFT JOIN Maps mp ON ps.map_id = mp.id
      LEFT JOIN Matches m ON mp.match_id = m.match_id
      WHERE ps.player = ?
      AND ps.team IS NOT NULL AND ps.team != ''
      GROUP BY ps.team
      ORDER BY last_match_date DESC
    `).all(playerName);
    
    return teams.map(t => ({
      team_name: normalizeTeamName(t.team_name),
      last_match_date: t.last_match_date,
    }));
  } catch (e) {
    // Fallback: just get distinct teams
    try {
      const teams = db.prepare(`
        SELECT DISTINCT team as team_name
        FROM Player_Stats
        WHERE player = ? AND team IS NOT NULL AND team != ''
      `).all(playerName);
      return teams.map(t => ({ team_name: normalizeTeamName(t.team_name), last_match_date: null }));
    } catch (e2) {
      return [];
    }
  }
}

export async function GET() {
  try {
    // Get all players with all their teams
    const allPlayerData = db.prepare(`
      SELECT DISTINCT 
        ps.player as player_name,
        ps.team as team_name
      FROM Player_Stats ps
      WHERE ps.player IS NOT NULL AND ps.player != ''
      ORDER BY ps.player
    `).all();
    
    // Group by player name and collect all teams
    const playersMap = new Map();
    
    allPlayerData.forEach(row => {
      const normalizedTeam = normalizeTeamName(row.team_name);
      
      // Skip showmatch teams
      if (isShowmatchTeam(normalizedTeam)) {
        return;
      }
      
      if (!playersMap.has(row.player_name)) {
        playersMap.set(row.player_name, {
          player_name: row.player_name,
          teams: [],
        });
      }
      
      // Add team if not already in list
      const player = playersMap.get(row.player_name);
      if (!player.teams.some(t => t.team_name === normalizedTeam)) {
        player.teams.push({ team_name: normalizedTeam });
      }
    });
    
    // For each player, get their most recent team and all teams
    const players = Array.from(playersMap.values()).map(player => {
      // Get all teams with dates
      const allTeams = getPlayerTeams(db, player.player_name);
      
      // Filter out showmatch teams
      const validTeams = allTeams.filter(t => !isShowmatchTeam(t.team_name));
      
      if (validTeams.length === 0) {
        return null;
      }
      
      // Most recent team is the first one (sorted by date DESC)
      const mostRecentTeam = validTeams[0];
      
      // Get last match date for inactivity check
      const lastMatchDate = mostRecentTeam.last_match_date || 
        getPlayerLastMatchDate(db, player.player_name);
      const isInactive = lastMatchDate ? isOlderThanSixMonths(lastMatchDate, null) : false;
      
      return {
        player_name: player.player_name,
        team_name: mostRecentTeam.team_name, // Most recent team for display
        all_teams: validTeams.map(t => t.team_name), // All teams for backend
        is_inactive: isInactive,
      };
    }).filter(p => p !== null);
    
    // Sort: active players first (by name), then inactive players (by name)
    players.sort((a, b) => {
      // Active players first
      if (a.is_inactive !== b.is_inactive) {
        return a.is_inactive ? 1 : -1;
      }
      // Then alphabetically
      return a.player_name.localeCompare(b.player_name);
    });
    
    return NextResponse.json(players);
  } catch (error) {
    console.error('Error fetching players:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
