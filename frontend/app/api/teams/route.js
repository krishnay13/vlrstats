// frontend/app/api/teams/route.js

import { NextResponse } from 'next/server';
import db from '../../lib/db.js';

export async function GET() {
  try {
    // Fetch all teams from the Teams table
    const teams = db.prepare('SELECT * FROM Teams').all();
    return NextResponse.json(teams);
  } catch (error) {
    console.error('Error fetching teams:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
