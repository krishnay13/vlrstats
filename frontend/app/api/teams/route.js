// frontend/app/api/teams/route.js

import { NextResponse } from 'next/server';
import db from '@/app/lib/db.js';
import { inferTeamRegion, isOlderThanSixMonths } from '@/app/lib/region-utils.js';
import { isShowmatchTeam, normalizeTeamName } from '@/app/lib/team-utils.js';

// Get team's last match date (checking all aliases)
function getTeamLastMatchDate(db, normalizedTeamName) {
  try {
    // Get all possible aliases for this team
    const allVariants = [normalizedTeamName];
    for (const [variant, canonical] of Object.entries({
      'via kru esports': 'KRÜ Esports',
      'via kru': 'KRÜ Esports',
      'kru esports': 'KRÜ Esports',
      'kru': 'KRÜ Esports',
      'visa kru esports': 'KRÜ Esports',
      'visa kru': 'KRÜ Esports',
      'movistar koi': 'KOI',
      'movistar koi(koi)': 'KOI',
      'koi': 'KOI',
    })) {
      if (canonical === normalizedTeamName) {
        allVariants.push(variant);
      }
    }
    
    const tableInfo = db.prepare("PRAGMA table_info(Matches)").all();
    const columns = tableInfo.map(col => col.name);
    const hasMatchDate = columns.includes('match_date');
    const hasMatchTsUtc = columns.includes('match_ts_utc');
    
    // Build query with all variants
    const placeholders = allVariants.map(() => '?').join(',');
    const params = [...allVariants, ...allVariants];
    
    let result;
    if (hasMatchDate && hasMatchTsUtc) {
      result = db.prepare(`
        SELECT MAX(COALESCE(match_date, substr(match_ts_utc, 1, 10))) as last_match_date
        FROM Matches
        WHERE (team_a IN (${placeholders}) OR team_b IN (${placeholders}))
        AND ((match_date IS NOT NULL AND match_date != '') OR (match_ts_utc IS NOT NULL AND match_ts_utc != ''))
      `).get(...params);
    } else if (hasMatchTsUtc) {
      result = db.prepare(`
        SELECT MAX(match_ts_utc) as last_match_date
        FROM Matches
        WHERE (team_a IN (${placeholders}) OR team_b IN (${placeholders}))
        AND match_ts_utc IS NOT NULL AND match_ts_utc != ''
      `).get(...params);
    } else if (hasMatchDate) {
      result = db.prepare(`
        SELECT MAX(match_date) as last_match_date
        FROM Matches
        WHERE (team_a IN (${placeholders}) OR team_b IN (${placeholders}))
        AND match_date IS NOT NULL AND match_date != ''
      `).get(...params);
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
    // Derive teams from Matches table (distinct team names)
    const teamNames = db.prepare(`
      SELECT DISTINCT team as team_name
      FROM (
        SELECT team_a as team FROM Matches WHERE team_a IS NOT NULL AND team_a != ''
        UNION
        SELECT team_b as team FROM Matches WHERE team_b IS NOT NULL AND team_b != ''
      )
      ORDER BY team_name
    `).all();
    
    // Normalize team names and merge aliases
    const normalizedTeamsMap = new Map();
    
    teamNames.forEach(team => {
      const normalized = normalizeTeamName(team.team_name);
      
      // Skip showmatch teams
      if (isShowmatchTeam(normalized)) {
        return;
      }
      
      // If we've seen this normalized name before, skip (merge aliases)
      if (normalizedTeamsMap.has(normalized)) {
        return;
      }
      
      normalizedTeamsMap.set(normalized, team.team_name);
    });
    
    // Convert to array and add region/inactive info
    const teams = Array.from(normalizedTeamsMap.keys()).map(teamName => {
      const region = inferTeamRegion(db, teamName);
      const lastMatchDate = getTeamLastMatchDate(db, teamName);
      const isInactive = lastMatchDate ? isOlderThanSixMonths(lastMatchDate, null) : false;
      
      return {
        team_name: teamName,
        region,
        is_inactive: isInactive,
      };
    });
    
    // Sort: by region, then active teams first, then alphabetically
    const regionOrder = { AMERICAS: 1, EMEA: 2, APAC: 3, CHINA: 4, UNKNOWN: 5 };
    teams.sort((a, b) => {
      // First by region
      const regionDiff = (regionOrder[a.region] || 99) - (regionOrder[b.region] || 99);
      if (regionDiff !== 0) return regionDiff;
      
      // Then active teams first
      if (a.is_inactive !== b.is_inactive) {
        return a.is_inactive ? 1 : -1;
      }
      
      // Finally alphabetically
      return (a.team_name || '').localeCompare(b.team_name || '');
    });
    
    return NextResponse.json(teams);
  } catch (error) {
    console.error('Error fetching teams:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
