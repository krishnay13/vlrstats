// frontend/app/api/players/route.js

import { NextResponse } from 'next/server';
import db from '@/app/lib/db.js';
import { isOlderThanSixMonths, inferTeamRegion } from '@/app/lib/region-utils.js';
import { isShowmatchTeam, normalizeTeamName } from '@/app/lib/team-utils.js';
import { getPlayerLastMatchDate, getPlayerTeams } from '@/app/lib/db/activity.js';
import { getTeamLogoUrl } from '@/app/lib/logos.js';

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
      
      // Determine most recent valid team (if any)
      const mostRecentTeam = validTeams[0] || null; // getPlayerTeams already sorts by date DESC
      
      // Get last match date for inactivity check (fallback to global last match if no valid teams)
      const lastMatchDate = (mostRecentTeam && mostRecentTeam.last_match_date) || 
        getPlayerLastMatchDate(db, player.player_name);
      const isInactive = lastMatchDate ? isOlderThanSixMonths(lastMatchDate, null) : false;

      // Get player statistics
      const stats = db.prepare(`
        SELECT 
          AVG(rating) as avg_rating,
          AVG(kills) as avg_kills,
          AVG(assists) as avg_assists,
          COUNT(DISTINCT map_id) as maps_played
        FROM Player_Stats
        WHERE player = ?
      `).get(player.player_name);

      // If no valid teams remain after filtering (e.g., only showmatch teams), treat as Free Agent
      if (!mostRecentTeam) {
        return {
          player_name: player.player_name,
          team_name: null,
          all_teams: [],
          is_inactive: isInactive,
          team_logo: null,
          region: 'UNKNOWN',
          avg_rating: stats?.avg_rating || 0,
          avg_kills: stats?.avg_kills || 0,
          avg_assists: stats?.avg_assists || 0,
          maps_played: stats?.maps_played || 0,
        };
      }
      
      // Ensure team name is normalized for logo/region lookups
      const normalizedTeamName = normalizeTeamName(mostRecentTeam.team_name);
      
      return {
        player_name: player.player_name,
        team_name: normalizedTeamName,
        all_teams: validTeams.map(t => normalizeTeamName(t.team_name)),
        is_inactive: isInactive,
        team_logo: getTeamLogoUrl(normalizedTeamName, 'small'),
        region: inferTeamRegion(db, normalizedTeamName),
        avg_rating: stats?.avg_rating || 0,
        avg_kills: stats?.avg_kills || 0,
        avg_assists: stats?.avg_assists || 0,
        maps_played: stats?.maps_played || 0,
      };
    });
    
    return NextResponse.json(players);
  } catch (error) {
    console.error('Error fetching players:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
