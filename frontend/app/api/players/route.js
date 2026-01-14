// frontend/app/api/players/route.js

import { NextResponse } from 'next/server';
import db from '@/app/lib/db.js';
import { isOlderThanSixMonths } from '@/app/lib/region-utils.js';
import { isShowmatchTeam, normalizeTeamName } from '@/app/lib/team-utils.js';
import { getPlayerLastMatchDate, getPlayerTeams } from '@/app/lib/db/activity.js';

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
