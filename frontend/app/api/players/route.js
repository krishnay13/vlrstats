// frontend/app/api/players/route.js

import { NextResponse } from 'next/server';
import db from '@/app/lib/db.js';
import { isOlderThanSixMonths } from '@/app/lib/region-utils.js';

// Helper function to check if team is a showmatch team
function isShowmatchTeam(teamName) {
  if (!teamName) return false;
  const name = teamName.toLowerCase();
  return name.includes('team international') || 
         name.includes('team spain') || 
         name.includes('team china') ||
         (name.includes('team ') && (name.includes('showmatch') || name.includes('all-star')));
}

// Get player's last match date
function getPlayerLastMatchDate(db, playerId) {
  try {
    const tableInfo = db.prepare("PRAGMA table_info(Matches)").all();
    const columns = tableInfo.map(col => col.name);
    const hasMatchDate = columns.includes('match_date');
    const hasMatchTsUtc = columns.includes('match_ts_utc');
    
    // First, get player's team name
    const player = db.prepare('SELECT team_name FROM Players WHERE player_id = ?').get(playerId);
    if (!player || !player.team_name) return null;
    
    // Then find matches where that team played
    let result;
    if (hasMatchDate && hasMatchTsUtc) {
      result = db.prepare(`
        SELECT MAX(COALESCE(match_date, substr(match_ts_utc, 1, 10))) as last_match_date
        FROM Matches m
        WHERE (m.team_a = ? OR m.team_b = ? OR m.team1_name = ? OR m.team2_name = ?)
        AND (match_date IS NOT NULL AND match_date != '') OR (match_ts_utc IS NOT NULL AND match_ts_utc != '')
      `).get(player.team_name, player.team_name, player.team_name, player.team_name);
    } else if (hasMatchTsUtc) {
      result = db.prepare(`
        SELECT MAX(match_ts_utc) as last_match_date
        FROM Matches m
        WHERE (m.team_a = ? OR m.team_b = ? OR m.team1_name = ? OR m.team2_name = ?)
        AND match_ts_utc IS NOT NULL AND match_ts_utc != ''
      `).get(player.team_name, player.team_name, player.team_name, player.team_name);
    } else if (hasMatchDate) {
      result = db.prepare(`
        SELECT MAX(match_date) as last_match_date
        FROM Matches m
        WHERE (m.team_a = ? OR m.team_b = ? OR m.team1_name = ? OR m.team2_name = ?)
        AND match_date IS NOT NULL AND match_date != ''
      `).get(player.team_name, player.team_name, player.team_name, player.team_name);
    } else {
      return null;
    }
    
    return result?.last_match_date || null;
  } catch (e) {
    // Alternative: check Player_Stats table directly
    try {
      const tableInfo = db.prepare("PRAGMA table_info(Player_Stats)").all();
      const columns = tableInfo.map(col => col.name);
      
      // Try to find last match through Player_Stats -> Maps -> Matches
      const result = db.prepare(`
        SELECT MAX(COALESCE(m.match_date, substr(m.match_ts_utc, 1, 10))) as last_match_date
        FROM Player_Stats ps
        JOIN Maps mp ON ps.map_id = mp.map_id
        JOIN Matches m ON mp.match_id = m.match_id
        WHERE ps.player_id = ?
        AND (m.match_date IS NOT NULL AND m.match_date != '') OR (m.match_ts_utc IS NOT NULL AND m.match_ts_utc != '')
      `).get(playerId);
      
      return result?.last_match_date || null;
    } catch (e2) {
      return null;
    }
  }
}

export async function GET() {
  try {
    // Fetch all players
    const allPlayers = db.prepare('SELECT * FROM Players').all();
    
    // Filter out players from showmatch teams and add inactive info
    const players = allPlayers
      .filter(player => !isShowmatchTeam(player.team_name))
      .map(player => {
        const lastMatchDate = getPlayerLastMatchDate(db, player.player_id);
        const isInactive = lastMatchDate ? isOlderThanSixMonths(lastMatchDate, null) : false;
        
        return {
          ...player,
          is_inactive: isInactive,
        };
      });
    
    return NextResponse.json(players);
  } catch (error) {
    console.error('Error fetching players:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
