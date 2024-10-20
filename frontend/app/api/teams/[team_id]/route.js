// frontend/app/api/teams/[team_id]/route.js

import { NextResponse } from 'next/server';
import db from '../../../lib/db.js';

export async function GET(request, { params }) {
  try {
    const { team_id } = params;

    // Fetch team details
    const team = db.prepare('SELECT * FROM Teams WHERE team_id = ?').get(team_id);
    if (!team) {
      return NextResponse.json({ error: 'Team not found' }, { status: 404 });
    }

    // Fetch players associated with the team
    const players = db.prepare('SELECT * FROM Players WHERE team_id = ?').all(team_id);

    return NextResponse.json({ team, players });
  } catch (error) {
    console.error('Error fetching team details:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
