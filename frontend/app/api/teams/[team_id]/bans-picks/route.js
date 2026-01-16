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
    
    // Convert to arrays, sorted by count
    const bans = Array.from(bansCounts.entries())
      .map(([map, count]) => ({ map, count }))
      .sort((a, b) => b.count - a.count);
    
    const picks = Array.from(picksCounts.entries())
      .map(([map, count]) => ({ map, count }))
      .sort((a, b) => b.count - a.count);

    return NextResponse.json({
      team_name: canonicalName,
      year: parseInt(year),
      bans,
      picks,
      total_matches_with_veto: matches.length,
    });
  } catch (error) {
    console.error('Error fetching bans/picks:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
