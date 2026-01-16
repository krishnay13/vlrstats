// frontend/app/api/matches/route.js

import { NextResponse } from 'next/server';
import db from '@/app/lib/db.js';
import { getTournamentSortPriority, getRegionFromMatchName, getRegionSortOrder } from '@/app/lib/region-utils.js';
import { isShowmatchTeam, normalizeTeamName } from '@/app/lib/team-utils.js';
import { getMatchesDateMeta, getMatchDateExpr } from '@/app/lib/db/schema.js';
import { getEventLogoUrl, getTeamLogoUrl } from '@/app/lib/logos.js';

// Normalize tournament name to base event name (removes stage-specific suffixes)
const normalizeEventName = (name) => {
  if (!name) return name;
  return name
    .replace(/\s*-\s*(playoffs?|group stage|swiss|bracket|finals?)\s*$/i, '')
    .replace(/\s*\(playoffs?|group stage|swiss|bracket|finals?\)\s*$/i, '')
    .trim();
};

export async function GET() {
  try {
    // Check which date columns exist and build a generic sort expression
    const dateMeta = getMatchesDateMeta(db);
    const dateExpr = getMatchDateExpr(dateMeta);

    const orderBy =
      dateExpr != null
        ? `ORDER BY ${dateExpr} DESC, match_id DESC`
        : 'ORDER BY match_id DESC';

    // Fetch completed matches only (exclude upcoming/TBD matches with NULL scores)
    const matches = db.prepare(`
      SELECT * FROM Matches 
      WHERE team_a_score IS NOT NULL AND team_b_score IS NOT NULL
      ${orderBy}
    `).all();
    
    // Filter out showmatch teams and process matches
    const processedMatches = matches
      .map(match => {
        // Handle both naming conventions and normalize
        const team1Raw = match.team_a || match.team1_name;
        const team2Raw = match.team_b || match.team2_name;
        const team1 = normalizeTeamName(team1Raw);
        const team2 = normalizeTeamName(team2Raw);
        
        // Filter out matches with showmatch teams or showmatch tournaments/stages
        if (isShowmatchTeam(team1) || isShowmatchTeam(team2)) {
          return null;
        }
        
        const tournament = match.tournament || 'Unknown Event';
        const stage = match.stage || '';
        const matchName = match.match_name || '';
        const matchNameLower = matchName.toLowerCase();
        const tournamentLower = tournament.toLowerCase();

        // Skip explicit showmatches / all-star style events
        if (
          stage.toLowerCase().includes('showmatch') ||
          matchNameLower.includes('showmatch') ||
          matchNameLower.includes('all-star') ||
          tournamentLower.includes('showmatch')
        ) {
          return null;
        }

        // Extract region from match_name, tournament, or stage
        let region = getRegionFromMatchName(matchName);
        if (region === 'UNKNOWN') {
          // Try to get region from tournament name (reuse tournamentLower already defined above)
          if (tournamentLower.includes('americas')) {
            region = 'AMERICAS';
          } else if (tournamentLower.includes('emea')) {
            region = 'EMEA';
          } else if (tournamentLower.includes('apac') || tournamentLower.includes('pacific')) {
            region = 'APAC';
          } else if (tournamentLower.includes('china')) {
            region = 'CHINA';
          }
        }

        // Extract year from tournament or match_name
        let yearMatch = tournament.match(/\b(202[0-9]|203[0-9])\b/);
        if (!yearMatch) {
          yearMatch = matchName.match(/\b(202[0-9]|203[0-9])\b/);
        }
        const year = yearMatch ? parseInt(yearMatch[1]) : 0;

        // Create group key for frontend:
        // - Within a year, we want: Kickoff -> Stage 1 -> Stage 2 -> Masters -> Champions
        // - Do NOT split Playoffs / Swiss / Group Stage into separate events.
        //
        // For VCT/Champions Tour events, the tournament name already encodes Stage 1/2/Kickoff,
        // and stage is usually "Swiss", "Playoffs", etc. We drop the sub-stage from the key
        // so that all sub-stages are grouped under the same event.
        //
        // For global events like Masters / Champions, we group by normalized tournament name.
        let groupKey;
        // Reuse tournamentLower and matchNameLower already defined above
        const isChampionsMain = (tournamentLower.includes('champions') && !tournamentLower.includes('champions tour')) ||
                                (matchNameLower.includes('champions') && !matchNameLower.includes('champions tour'));
        const isMasters = tournamentLower.includes('masters') || matchNameLower.includes('masters');

        if (isChampionsMain || isMasters) {
          // Champions and Masters tournaments: normalize name to group playoffs and group stage
          groupKey = normalizeEventName(tournament);
        } else {
          // VCT / regional leagues: group by normalized tournament + region
          const normalizedTournament = normalizeEventName(tournament);
          if (region !== 'UNKNOWN') {
            groupKey = `${normalizedTournament} - ${region}`;
          } else {
            groupKey = normalizedTournament;
          }
        }
        
        // Derive safe match scores for frontend (avoid treating 0 as falsy)
        const team1Score = match.team_a_score ?? match.team1_score ?? 0;
        const team2Score = match.team_b_score ?? match.team2_score ?? 0;

        return {
          ...match,
          tournament,
          stage,
          region,
          year,
          groupKey,
          team1_name: team1,
          team2_name: team2,
          team1_score: team1Score,
          team2_score: team2Score,
          team1_logo: getTeamLogoUrl(team1, 'small'),
          team2_logo: getTeamLogoUrl(team2, 'small'),
          event_logo: getEventLogoUrl({ region, tournament }),
        };
      })
      .filter(match => match !== null);
    
    // Group by groupKey
    const grouped = {};
    processedMatches.forEach(match => {
      const key = match.groupKey;
      if (!grouped[key]) {
        grouped[key] = [];
      }
      grouped[key].push(match);
    });
    
    // Sort tournaments by priority: year -> tournament type -> stage -> region
    const sortedTournaments = Object.keys(grouped).sort((a, b) => {
      // Get the first match from each group to extract info
      const matchA = grouped[a][0];
      const matchB = grouped[b][0];
      
      const priorityA = getTournamentSortPriority(matchA.tournament, matchA.stage);
      const priorityB = getTournamentSortPriority(matchB.tournament, matchB.stage);
      
      // 1. Sort by year (newer first: 2025 before 2024)
      if (priorityA.year !== priorityB.year) {
        return priorityB.year - priorityA.year;
      }
      
      // 2. Sort by tournament priority (Champions > Masters > VCT/Champions Tour)
      if (priorityA.tournamentPriority !== priorityB.tournamentPriority) {
        return priorityB.tournamentPriority - priorityA.tournamentPriority;
      }
      
      // 3. Sort by stage priority (Playoffs > Stage 2 > Stage 1 > Kickoff)
      if (priorityA.stagePriority !== priorityB.stagePriority) {
        return priorityB.stagePriority - priorityA.stagePriority;
      }
      
      // 4. Sort by region (Americas > EMEA > APAC > China)
      const regionOrderA = getRegionSortOrder(matchA.region);
      const regionOrderB = getRegionSortOrder(matchB.region);
      if (regionOrderA !== regionOrderB) {
        return regionOrderA - regionOrderB;
      }
      
      // 5. Finally alphabetical
      return a.localeCompare(b);
    });
    
    // Rebuild grouped object with sorted tournaments
    const sortedGrouped = {};
    sortedTournaments.forEach(tournament => {
      sortedGrouped[tournament] = grouped[tournament];
    });
    
    // Group by year for easier frontend consumption
    const groupedByYear = {};
    Object.keys(sortedGrouped).forEach(tournamentKey => {
      const matches = sortedGrouped[tournamentKey];
      const year = matches[0]?.year || 0;
      if (!groupedByYear[year]) {
        groupedByYear[year] = {};
      }
      groupedByYear[year][tournamentKey] = matches;
    });
    
    return NextResponse.json({
      matches: processedMatches,
      grouped: sortedGrouped,
      groupedByYear: groupedByYear,
    });
  } catch (error) {
    console.error('Error fetching matches:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
