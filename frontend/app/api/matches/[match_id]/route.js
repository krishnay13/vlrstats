// frontend/app/api/matches/[match_id]/route.js

import { NextResponse } from 'next/server';
import db from '../../../lib/db.js';

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
    const maps = db.prepare('SELECT * FROM Maps WHERE match_id = ?').all(match_id);

    // For each map, fetch player stats
    const mapsWithStats = maps.map((map) => {
      const playerStats = db.prepare('SELECT * FROM Player_Stats WHERE map_id = ?').all(map.map_id);

      // Replace player IDs with player names
      const playerStatsWithNames = playerStats.map((stat) => {
        const player = db.prepare('SELECT player_name FROM Players WHERE player_id = ?').get(stat.player_id);
        return { ...stat, player_name: player ? player.player_name : 'Unknown' };
      });

      return { ...map, playerStats: playerStatsWithNames };
    });

    // Fetch player stats for match totals (where map_id is NULL)
    const playerStats = db.prepare('SELECT * FROM Player_Stats WHERE match_id = ? AND map_id IS NULL').all(match_id);

    // Replace player IDs with player names in match totals
    const playerStatsWithNames = playerStats.map((stat) => {
      const player = db.prepare('SELECT player_name FROM Players WHERE player_id = ?').get(stat.player_id);
      return { ...stat, player_name: player ? player.player_name : 'Unknown' };
    });

    return NextResponse.json({ match, maps: mapsWithStats, playerStats: playerStatsWithNames });
  } catch (error) {
    console.error('Error fetching match details:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
