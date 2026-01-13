// frontend/app/api/stats/route.js

import { NextResponse } from 'next/server';
import db from '@/app/lib/db.js';
import { normalizeTeamName } from '@/app/lib/team-utils.js';

export async function GET() {
  try {
    // Get counts from database
    const matchCount = db.prepare('SELECT COUNT(*) as count FROM Matches').get();
    
    // Derive teams from Matches table (distinct team names, normalized)
    const teamNames = db.prepare(`
      SELECT DISTINCT team
      FROM (
        SELECT team_a as team FROM Matches WHERE team_a IS NOT NULL AND team_a != ''
        UNION
        SELECT team_b as team FROM Matches WHERE team_b IS NOT NULL AND team_b != ''
      )
    `).all();
    
    // Normalize team names to merge aliases
    const normalizedTeams = new Set();
    teamNames.forEach(row => {
      const normalized = normalizeTeamName(row.team);
      if (normalized) {
        normalizedTeams.add(normalized);
      }
    });
    
    const teamCount = { count: normalizedTeams.size };
    
    // Derive players from Player_Stats table
    const playerCount = db.prepare("SELECT COUNT(DISTINCT player) as count FROM Player_Stats WHERE player IS NOT NULL AND player != ''").get();
    
    // Get unique tournament count
    let tournamentCount = { count: 0 };
    try {
      tournamentCount = db.prepare("SELECT COUNT(DISTINCT tournament) as count FROM Matches WHERE tournament IS NOT NULL AND tournament != ''").get();
    } catch (e) {
      // Tournament field might not exist, default to 0
    }

    return NextResponse.json({
      matches: matchCount?.count || 0,
      teams: teamCount?.count || 0,
      players: playerCount?.count || 0,
      tournaments: tournamentCount?.count || 0,
    });
  } catch (error) {
    console.error('Error fetching stats:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
