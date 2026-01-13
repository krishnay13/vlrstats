// frontend/app/api/teams/route.js

import { NextResponse } from 'next/server';
import db from '@/app/lib/db.js';
import { getRegionFromTournament, getRegionFromTeam, isOlderThanSixMonths } from '@/app/lib/region-utils.js';

// Helper function to check if team is a showmatch team
function isShowmatchTeam(teamName) {
  if (!teamName) return false;
  const name = teamName.toLowerCase();
  return name.includes('team international') || 
         name.includes('team spain') || 
         name.includes('team china') ||
         (name.includes('team ') && (name.includes('showmatch') || name.includes('all-star')));
}

// Get team's region based on tournaments they've played in
function getTeamRegion(db, teamName) {
  try {
    // Get tournaments this team has played in
    const tournaments = db.prepare(`
      SELECT DISTINCT tournament 
      FROM Matches 
      WHERE (team_a = ? OR team_b = ?) 
      AND tournament IS NOT NULL 
      AND tournament != ''
      LIMIT 50
    `).all(teamName, teamName);
    
    // Count regions from tournaments
    const regionCounts = { APAC: 0, CHINA: 0, EMEA: 0, AMERICAS: 0 };
    tournaments.forEach(t => {
      const region = getRegionFromTournament(t.tournament);
      if (region !== 'UNKNOWN') {
        regionCounts[region] = (regionCounts[region] || 0) + 1;
      }
    });
    
    // Return the most common region
    const maxCount = Math.max(...Object.values(regionCounts));
    if (maxCount > 0) {
      for (const [region, count] of Object.entries(regionCounts)) {
        if (count === maxCount) {
          return region;
        }
      }
    }
    
    // Fallback to team name detection
    return getRegionFromTeam(teamName);
  } catch (e) {
    return getRegionFromTeam(teamName);
  }
}

// Get team's last match date
function getTeamLastMatchDate(db, teamName) {
  try {
    const tableInfo = db.prepare("PRAGMA table_info(Matches)").all();
    const columns = tableInfo.map(col => col.name);
    const hasMatchDate = columns.includes('match_date');
    const hasMatchTsUtc = columns.includes('match_ts_utc');
    
    let result;
    if (hasMatchDate && hasMatchTsUtc) {
      result = db.prepare(`
        SELECT MAX(COALESCE(match_date, substr(match_ts_utc, 1, 10))) as last_match_date
        FROM Matches
        WHERE (team_a = ? OR team_b = ? OR team1_name = ? OR team2_name = ?)
        AND ((match_date IS NOT NULL AND match_date != '') OR (match_ts_utc IS NOT NULL AND match_ts_utc != ''))
      `).get(teamName, teamName, teamName, teamName);
    } else if (hasMatchTsUtc) {
      result = db.prepare(`
        SELECT MAX(match_ts_utc) as last_match_date
        FROM Matches
        WHERE (team_a = ? OR team_b = ? OR team1_name = ? OR team2_name = ?)
        AND match_ts_utc IS NOT NULL AND match_ts_utc != ''
      `).get(teamName, teamName, teamName, teamName);
    } else if (hasMatchDate) {
      result = db.prepare(`
        SELECT MAX(match_date) as last_match_date
        FROM Matches
        WHERE (team_a = ? OR team_b = ? OR team1_name = ? OR team2_name = ?)
        AND match_date IS NOT NULL AND match_date != ''
      `).get(teamName, teamName, teamName, teamName);
    } else {
      return null;
    }
    
    return result?.last_match_date || null;
  } catch (e) {
    return null;
  }
}

export async function GET() {
  try {
    // Fetch all teams from the Teams table
    const allTeams = db.prepare('SELECT * FROM Teams').all();
    
    // Filter out showmatch teams and add region/inactive info
    const teams = allTeams
      .filter(team => !isShowmatchTeam(team.team_name))
      .map(team => {
        const region = getTeamRegion(db, team.team_name);
        const lastMatchDate = getTeamLastMatchDate(db, team.team_name);
        const isInactive = lastMatchDate ? isOlderThanSixMonths(lastMatchDate, null) : false;
        
        return {
          ...team,
          region,
          is_inactive: isInactive,
        };
      });
    
    // Sort by region, then by team name
    const regionOrder = { AMERICAS: 1, EMEA: 2, APAC: 3, CHINA: 4, UNKNOWN: 5 };
    teams.sort((a, b) => {
      const regionDiff = (regionOrder[a.region] || 99) - (regionOrder[b.region] || 99);
      if (regionDiff !== 0) return regionDiff;
      return (a.team_name || '').localeCompare(b.team_name || '');
    });
    
    return NextResponse.json(teams);
  } catch (error) {
    console.error('Error fetching teams:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
