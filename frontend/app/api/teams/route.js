// frontend/app/api/teams/route.js

import { NextResponse } from 'next/server';
import db from '@/app/lib/db.js';
import { inferTeamRegion, isOlderThanSixMonths } from '@/app/lib/region-utils.js';
import { isShowmatchTeam, normalizeTeamName } from '@/app/lib/team-utils.js';
import { getTeamLastMatchDate } from '@/app/lib/db/activity.js';
import { getTeamLogoUrl } from '@/app/lib/logos.js';

// Teams that have been removed from VCT 2026
const INACTIVE_TEAMS = [
  'Bleed',
  'Bleed Esports',
  'KOI',
  'Talon',
  'Talon Esports',
  '2G Esports',
  '2G',
  'Boom Esports',
  'Boom',
  'Apeks',
];

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
    
    // Convert to array and add region/inactive info and 2026 stats
    const teams = Array.from(normalizedTeamsMap.keys()).map(teamName => {
      const region = inferTeamRegion(db, teamName);
      const lastMatchDate = getTeamLastMatchDate(db, teamName);
      
      // Check if team is in the inactive list
      const isInInactiveList = INACTIVE_TEAMS.some(
        inactiveTeam => teamName.toLowerCase() === inactiveTeam.toLowerCase()
      );
      
      // Team is inactive if in the inactive list OR hasn't played in 6 months
      const isInactive = isInInactiveList || (lastMatchDate ? isOlderThanSixMonths(lastMatchDate, null) : false);
      
      // Calculate 2026 statistics
      // Get match record (wins/losses) for 2026
      const matchStats = db.prepare(`
        SELECT 
          COUNT(*) as total_matches,
          SUM(CASE 
            WHEN (team_a = ? AND match_result = 'team_a_win') OR 
                 (team_b = ? AND match_result = 'team_b_win') THEN 1 
            ELSE 0 
          END) as wins,
          SUM(CASE 
            WHEN (team_a = ? AND match_result = 'team_b_win') OR 
                 (team_b = ? AND match_result = 'team_a_win') THEN 1 
            ELSE 0 
          END) as losses
        FROM Matches
        WHERE (team_a = ? OR team_b = ?)
          AND match_date >= '2026-01-01'
      `).get(teamName, teamName, teamName, teamName, teamName, teamName);
      
      // Get map record for 2026
      const mapStats = db.prepare(`
        SELECT 
          COUNT(*) as total_maps,
          SUM(CASE 
            WHEN (team_a = ? AND team_a_score > team_b_score) OR 
                 (team_b = ? AND team_b_score > team_a_score) THEN 1 
            ELSE 0 
          END) as map_wins,
          SUM(CASE 
            WHEN (team_a = ? AND team_a_score < team_b_score) OR 
                 (team_b = ? AND team_b_score < team_a_score) THEN 1 
            ELSE 0 
          END) as map_losses
        FROM Matches
        WHERE (team_a = ? OR team_b = ?)
          AND match_date >= '2026-01-01'
      `).get(teamName, teamName, teamName, teamName, teamName, teamName);
      
      // Calculate round differential for 2026
      const roundDiff = db.prepare(`
        SELECT 
          SUM(CASE WHEN team_a = ? THEN team_a_score ELSE 0 END) as rounds_for_a,
          SUM(CASE WHEN team_a = ? THEN team_b_score ELSE 0 END) as rounds_against_a,
          SUM(CASE WHEN team_b = ? THEN team_b_score ELSE 0 END) as rounds_for_b,
          SUM(CASE WHEN team_b = ? THEN team_a_score ELSE 0 END) as rounds_against_b
        FROM Matches
        WHERE (team_a = ? OR team_b = ?)
          AND match_date >= '2026-01-01'
      `).get(teamName, teamName, teamName, teamName, teamName, teamName);
      
      const roundsFor = (roundDiff?.rounds_for_a || 0) + (roundDiff?.rounds_for_b || 0);
      const roundsAgainst = (roundDiff?.rounds_against_a || 0) + (roundDiff?.rounds_against_b || 0);
      const roundDifferential = roundsFor - roundsAgainst;
      
      return {
        team_name: teamName,
        region,
        is_inactive: isInactive,
        logo_url: getTeamLogoUrl(teamName, 'small'),
        match_wins: matchStats?.wins || 0,
        match_losses: matchStats?.losses || 0,
        map_wins: mapStats?.map_wins || 0,
        map_losses: mapStats?.map_losses || 0,
        round_differential: roundDifferential,
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
