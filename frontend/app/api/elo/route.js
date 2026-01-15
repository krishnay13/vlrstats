// frontend/app/api/elo/route.js

import { NextResponse } from 'next/server'
import db from '@/app/lib/db.js'

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url)
    const topTeams = Number(searchParams.get('topTeams') || 6)
    const topPlayers = Number(searchParams.get('topPlayers') || 6)

    const teams = db
      .prepare(
        `
        SELECT team, rating, matches
        FROM Elo_Current
        ORDER BY rating DESC
        LIMIT ?
        `
      )
      .all(topTeams)

    const players = db
      .prepare(
        `
        SELECT player, team, rating, matches
        FROM Player_Elo_Current
        ORDER BY rating DESC
        LIMIT ?
        `
      )
      .all(topPlayers)

    return NextResponse.json({ teams, players })
  } catch (error) {
    console.error('Error fetching Elo data:', error)
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
  }
}
