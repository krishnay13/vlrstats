// frontend/app/api/stats/route.js

import { NextResponse } from 'next/server';
import db from '@/app/lib/db.js';

export async function GET() {
  try {
    // Get counts from database
    const matchCount = db.prepare('SELECT COUNT(*) as count FROM Matches').get();
    const teamCount = db.prepare('SELECT COUNT(*) as count FROM Teams').get();
    const playerCount = db.prepare('SELECT COUNT(*) as count FROM Players').get();
    
    // Get unique tournament count (if there's a tournament field)
    let tournamentCount = { count: 0 };
    try {
      tournamentCount = db.prepare('SELECT COUNT(DISTINCT tournament) as count FROM Matches WHERE tournament IS NOT NULL AND tournament != ""').get();
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
