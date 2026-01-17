// frontend/app/api/teams/[team_id]/bans-picks/route.js

import { NextResponse } from 'next/server';
import db from '@/app/lib/db.js';
import { normalizeTeamName } from '@/app/lib/team-utils.js';

/**
 * Parse bans/picks string and extract individual actions.
 * Example: "ENVY ban Haven; EG ban Bind; ENVY pick Abyss; EG pick Corrode; ENVY ban Pearl; EG ban Split; Bind remains"
 * Returns: { bans: [{ team, map }, ...], picks: [{ team, map }, ...] }
 */
function parseBansPicks(banPicksStr) {
  if (!banPicksStr) return { bans: [], picks: [] };

  const bans = [];
  const picks = [];
  
  // Split by semicolon
  const actions = banPicksStr.split(';').map(s => s.trim()).filter(s => s);
  
  for (const action of actions) {
    const lowerAction = action.toLowerCase();
    
    // Skip "remains" statements like "Bind remains"
    if (lowerAction.includes('remains')) {
      continue;
    }
    
    // Match patterns like "ENVY ban Haven" or "EG pick Abyss"
    const banMatch = action.match(/^([A-Za-z0-9\s]+?)\s+ban\s+([A-Za-z0-9\s]+)$/i);
    if (banMatch) {
      bans.push({
        team: banMatch[1].trim(),
        map: banMatch[2].trim()
      });
      continue;
    }
    
    const pickMatch = action.match(/^([A-Za-z0-9\s]+?)\s+pick\s+([A-Za-z0-9\s]+)$/i);
    if (pickMatch) {
      picks.push({
        team: pickMatch[1].trim(),
        map: pickMatch[2].trim()
      });
    }
  }
  
  return { bans, picks };
}

export async function GET(request, { params }) {
  try {
    const { team_id } = params;
    const { searchParams } = new URL(request.url);
    const year = searchParams.get('year') || '2026';

    const decodedName = decodeURIComponent(team_id);
    const canonicalName = normalizeTeamName(decodedName);
    
    // Query all matches for this team in the given year that have bans_picks data
    const matches = db.prepare(`
      SELECT bans_picks FROM Matches
      WHERE bans_picks IS NOT NULL AND bans_picks != ''
        AND match_date >= ? AND match_date < ?
        AND (LOWER(team_a) = LOWER(?) OR LOWER(team_b) = LOWER(?))
    `).all(`${year}-01-01`, `${parseInt(year) + 1}-01-01`, canonicalName, canonicalName);

    // Aggregate bans and picks
    const bansCounts = new Map(); // map -> count
    const picksCounts = new Map();
    
    for (const match of matches) {
      const { bans, picks } = parseBansPicks(match.bans_picks);
      
      for (const ban of bans) {
        // Normalize team name from veto string and compare
        const normalizedBanTeam = normalizeTeamName(ban.team);
        
        // Only count if this team banned it
        if (normalizedBanTeam.toLowerCase() === canonicalName.toLowerCase()) {
          const map = ban.map.toLowerCase();
          bansCounts.set(map, (bansCounts.get(map) || 0) + 1);
        }
      }
      
      for (const pick of picks) {
        // Normalize team name from veto string and compare
        const normalizedPickTeam = normalizeTeamName(pick.team);
        
        // Only count if this team picked it
        if (normalizedPickTeam.toLowerCase() === canonicalName.toLowerCase()) {
          const map = pick.map.toLowerCase();
          picksCounts.set(map, (picksCounts.get(map) || 0) + 1);
        }
      }
    }

    // Query map winrates with detailed match info for this team in the given year
    const mapMatches = db.prepare(`
      SELECT 
        LOWER(m.map) as map_name,
        mat.match_id,
        mat.team_a,
        mat.team_b,
        m.team_a_score,
        m.team_b_score,
        mat.match_date,
        CASE 
          WHEN LOWER(mat.team_a) = LOWER(?) THEN mat.team_b
          WHEN LOWER(mat.team_b) = LOWER(?) THEN mat.team_a
          ELSE NULL
        END as opponent,
        CASE 
          WHEN (LOWER(mat.team_a) = LOWER(?) AND m.team_a_score > m.team_b_score) OR 
               (LOWER(mat.team_b) = LOWER(?) AND m.team_b_score > m.team_a_score) THEN 'W'
          ELSE 'L'
        END as result,
        CASE 
          WHEN LOWER(mat.team_a) = LOWER(?) THEN m.team_a_score
          ELSE m.team_b_score
        END as team_score,
        CASE 
          WHEN LOWER(mat.team_a) = LOWER(?) THEN m.team_b_score
          ELSE m.team_a_score
        END as opponent_score
      FROM Maps m
      JOIN Matches mat ON m.match_id = mat.match_id
      WHERE (LOWER(mat.team_a) = LOWER(?) OR LOWER(mat.team_b) = LOWER(?))
        AND mat.match_date >= ? AND mat.match_date < ?
        AND m.map IS NOT NULL AND m.map != ''
      ORDER BY LOWER(m.map), mat.match_date DESC
    `).all(canonicalName, canonicalName, canonicalName, canonicalName, canonicalName, canonicalName, canonicalName, canonicalName, `${year}-01-01`, `${parseInt(year) + 1}-01-01`);

    // Organize matches by map
    const matchesByMap = new Map();
    for (const match of mapMatches) {
      if (!matchesByMap.has(match.map_name)) {
        matchesByMap.set(match.map_name, []);
      }
      matchesByMap.get(match.map_name).push({
        match_id: match.match_id,
        date: match.match_date,
        opponent: normalizeTeamName(match.opponent),
        scoreline: `${match.team_score}-${match.opponent_score}`,
        result: match.result
      });
    }

    // Query map winrates for this team in the given year
    const mapWinrates = db.prepare(`
      SELECT 
        LOWER(m.map) as map_name,
        COUNT(*) as total_maps,
        SUM(CASE 
          WHEN (LOWER(mat.team_a) = LOWER(?) AND m.team_a_score > m.team_b_score) OR 
               (LOWER(mat.team_b) = LOWER(?) AND m.team_b_score > m.team_a_score) THEN 1 
          ELSE 0 
        END) as wins
      FROM Maps m
      JOIN Matches mat ON m.match_id = mat.match_id
      WHERE (LOWER(mat.team_a) = LOWER(?) OR LOWER(mat.team_b) = LOWER(?))
        AND mat.match_date >= ? AND mat.match_date < ?
        AND m.map IS NOT NULL AND m.map != ''
      GROUP BY LOWER(m.map)
      ORDER BY total_maps DESC, wins DESC
    `).all(canonicalName, canonicalName, canonicalName, canonicalName, `${year}-01-01`, `${parseInt(year) + 1}-01-01`);

    // Convert winrates to structured format with percentages
    const mapWinratesByName = new Map();
    for (const row of mapWinrates) {
      const winPercent = row.total_maps > 0 ? Math.round((row.wins / row.total_maps) * 100) : 0;
      mapWinratesByName.set(row.map_name, {
        map: row.map_name,
        wins: row.wins,
        total: row.total_maps,
        losses: row.total_maps - row.wins,
        winPercent,
        matches: matchesByMap.get(row.map_name) || []
      });
    }
    
    // Convert to arrays, sorted by count
    const bans = Array.from(bansCounts.entries())
      .map(([map, count]) => ({ 
        map, 
        count,
        winrate: mapWinratesByName.get(map)
      }))
      .sort((a, b) => b.count - a.count);
    
    const picks = Array.from(picksCounts.entries())
      .map(([map, count]) => ({ 
        map, 
        count,
        winrate: mapWinratesByName.get(map)
      }))
      .sort((a, b) => b.count - a.count);

    // Get all maps with winrates (even ones not banned/picked)
    const allMapWinrates = Array.from(mapWinratesByName.values())
      .sort((a, b) => b.winPercent - a.winPercent);

    return NextResponse.json({
      team_name: canonicalName,
      year: parseInt(year),
      bans,
      picks,
      map_winrates: allMapWinrates,
      total_matches_with_veto: matches.length,
    });
  } catch (error) {
    console.error('Error fetching bans/picks:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
