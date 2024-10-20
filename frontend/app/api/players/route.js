// frontend/app/api/players/route.js

import { NextResponse } from 'next/server';
import db from '../../lib/db';

export async function GET() {
  try {
    const players = db.prepare('SELECT * FROM Players').all();
    return NextResponse.json(players);
  } catch (error) {
    console.error('Error fetching players:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
