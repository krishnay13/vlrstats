// frontend/app/api/matches/[match_id]/route.js

import { NextResponse } from 'next/server';
import db from '@/app/lib/db.js';
import { normalizeTeamName } from '@/app/lib/team-utils.js';
import { getTeamLogoUrl } from '@/app/lib/logos.js';

export async function GET(request, { params }) {
  try {
    const { match_id } = params;

    // Fetch match details
    const match = db.prepare('SELECT * FROM Matches WHERE match_id = ?').get(match_id);
    if (!match) {
      console.error(`Match with ID ${match_id} not found.`);
      return NextResponse.json({ error: 'Match not found' }, { status: 404 });
    }

    // Fetch maps associated with the match
    const maps = db.prepare('SELECT * FROM Maps WHERE match_id = ? ORDER BY game_id').all(match_id);

    // For each map, fetch player stats
    const mapsWithStats = maps.map((map) => {
      // Maps table uses 'id' as primary key, not 'map_id'
      const mapId = map.id;
      const playerStats = db.prepare('SELECT * FROM Player_Stats WHERE map_id = ?').all(mapId);

      // Player_Stats table uses 'player' (string) directly, not player_id
      // Just ensure we have the right field names
      const playerStatsWithNames = playerStats.map((stat) => {
        return { 
          ...stat,
          player_name: stat.player || 'Unknown',
          team_name: stat.team || null
        };
      });

      // Clean map name - remove leading numbers
      const cleanMapName = map.map ? map.map.replace(/^\d+/, '') : map.map;
      
      // Get team names from match for display
      const team1Name = normalizeTeamName(match.team_a || match.team1_name);
      const team2Name = normalizeTeamName(match.team_b || match.team2_name);

      return { 
        ...map, 
        map_id: mapId, // Add map_id alias for frontend compatibility
        map_name: cleanMapName, // Add map_name alias
        team1_name: team1Name,
        team2_name: team2Name,
        team1_logo: getTeamLogoUrl(team1Name, 'large'),
        team2_logo: getTeamLogoUrl(team2Name, 'large'),
        team1_score: map.team_a_score || 0,
        team2_score: map.team_b_score || 0,
        playerStats: playerStatsWithNames 
      };
    });

    // Fetch player stats for match totals (where map_id is NULL)
    const playerStats = db.prepare('SELECT * FROM Player_Stats WHERE match_id = ? AND map_id IS NULL').all(match_id);

    // Replace player IDs with player names and team names in match totals
    // Player_Stats table uses 'player' (string) directly, not player_id
    const playerStatsWithNames = playerStats.map((stat) => {
      return { 
        ...stat,
        player_name: stat.player || 'Unknown',
        team_name: stat.team || null
      };
    });

    const matchTeam1 = normalizeTeamName(match.team_a || match.team1_name);
    const matchTeam2 = normalizeTeamName(match.team_b || match.team2_name);

    return NextResponse.json({
      match: {
        ...match,
        team1_name: matchTeam1,
        team2_name: matchTeam2,
        team1_logo: getTeamLogoUrl(matchTeam1, 'large'),
        team2_logo: getTeamLogoUrl(matchTeam2, 'large'),
      },
      maps: mapsWithStats,
      playerStats: playerStatsWithNames,
    });
  } catch (error) {
    console.error('Error fetching match details:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
