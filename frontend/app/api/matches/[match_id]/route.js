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
      // Preserve insertion order to keep team assignment by index stable
      const playerStats = db.prepare('SELECT * FROM Player_Stats WHERE map_id = ? ORDER BY rowid').all(mapId);

      // Player_Stats table uses 'player' (string) directly, not player_id
      // Just ensure we have the right field names
      const team1Name = normalizeTeamName(match.team_a || match.team1_name);
      const team2Name = normalizeTeamName(match.team_b || match.team2_name);

      // Assign team by index (first 5 -> team1, next 5 -> team2),
      // fallback to normalized stat.team when available,
      // and handle rare 6th man by balancing assignments.
      let t1Count = 0;
      let t2Count = 0;
      const playerStatsWithNames = playerStats.map((stat, idx) => {
        const player_name = stat.player || 'Unknown';
        const normalizedStatTeam = stat.team ? normalizeTeamName(stat.team) : null;
        let team_name = null;

        if (normalizedStatTeam === team1Name) {
          team_name = team1Name; t1Count++;
        } else if (normalizedStatTeam === team2Name) {
          team_name = team2Name; t2Count++;
        } else if (idx < 5) {
          team_name = team1Name; t1Count++;
        } else if (idx < 10) {
          team_name = team2Name; t2Count++;
        } else {
          // Assign extra players to the team with fewer assigned so far
          if (t1Count <= t2Count) { team_name = team1Name; t1Count++; }
          else { team_name = team2Name; t2Count++; }
        }

        return {
          ...stat,
          player_name,
          team_name,
        };
      });

      // Clean map name - remove leading numbers
      const cleanMapName = map.map
        ? map.map
            .replace(/^\d+\s*-?\s*/, '')
            .replace(/\s*\(pick\)/gi, '')
            .replace(/pick/gi, '')
            .replace(/\s*\d{1,2}:\d{2}\s*(AM|PM)?/gi, '')
            .replace(/:\d+$/i, '')
            .trim()
        : map.map;
      
      // Get team names from match for display
      // team names already computed above

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
    const playerStats = db.prepare('SELECT * FROM Player_Stats WHERE match_id = ? AND map_id IS NULL ORDER BY rowid').all(match_id);

    // Replace player IDs with player names and team names in match totals
    // Player_Stats table uses 'player' (string) directly, not player_id
    // Apply same assignment logic for totals (if present)
    let t1Total = 0;
    let t2Total = 0;
    const playerStatsWithNames = playerStats.map((stat, idx) => {
      const player_name = stat.player || 'Unknown';
      const normalizedStatTeam = stat.team ? normalizeTeamName(stat.team) : null;
      let team_name = null;

      if (normalizedStatTeam === matchTeam1) {
        team_name = matchTeam1; t1Total++;
      } else if (normalizedStatTeam === matchTeam2) {
        team_name = matchTeam2; t2Total++;
      } else if (idx < 5) {
        team_name = matchTeam1; t1Total++;
      } else if (idx < 10) {
        team_name = matchTeam2; t2Total++;
      } else {
        if (t1Total <= t2Total) { team_name = matchTeam1; t1Total++; }
        else { team_name = matchTeam2; t2Total++; }
      }

      return {
        ...stat,
        player_name,
        team_name,
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
