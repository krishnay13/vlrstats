// frontend/app/api/matches/route.js

import { NextResponse } from 'next/server';
import db from '../../lib/db.js';

export async function GET() {
  try {
    // Fetch all matches from the Matches table
    const matches = db.prepare('SELECT * FROM Matches').all();
    return NextResponse.json(matches);
  } catch (error) {
    console.error('Error fetching matches:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
