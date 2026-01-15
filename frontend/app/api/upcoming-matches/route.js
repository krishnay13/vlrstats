// frontend/app/api/upcoming-matches/route.js

import { NextResponse } from 'next/server';
import db from '@/app/lib/db.js';
import { isShowmatchTeam, normalizeTeamName } from '@/app/lib/team-utils.js';
import { getMatchesDateMeta, getMatchDateExpr, getMatchDateNonEmptyWhere } from '@/app/lib/db/schema.js';
import { getEventLogoUrl, getTeamLogoUrl } from '@/app/lib/logos.js';

export async function GET() {
  try {
    const dateMeta = getMatchesDateMeta(db);
    const dateExpr = getMatchDateExpr(dateMeta);
    const nonEmptyWhere = getMatchDateNonEmptyWhere(dateMeta);

    if (!dateExpr || !nonEmptyWhere) {
      // No date columns available, return empty array
      return NextResponse.json([]);
    }

    // Get current date in YYYY-MM-DD format
    const now = new Date();
    const today = now.toISOString().split('T')[0];

    // Query matches where date is in the future
    // Use the date expression to handle both match_date and match_ts_utc
    const sql = `
      SELECT *
      FROM Matches
      WHERE ${nonEmptyWhere}
      AND ${dateExpr} > ?
      ORDER BY ${dateExpr} ASC
      LIMIT 8
    `;

    const matches = db.prepare(sql).all(today);

    // Filter out showmatches and process matches
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

        // Get match date for display
        const matchDate = match.match_date || (match.match_ts_utc ? match.match_ts_utc.split('T')[0] : null);

        return {
          match_id: match.match_id,
          team_a: team1,
          team_b: team2,
          team_a_score: match.team_a_score || match.team1_score || null,
          team_b_score: match.team_b_score || match.team2_score || null,
          tournament: tournament,
          stage: stage,
          match_name: matchName,
          match_date: matchDate,
          match_ts_utc: match.match_ts_utc,
          team_a_logo: getTeamLogoUrl(team1, 'small'),
          team_b_logo: getTeamLogoUrl(team2, 'small'),
          tournament_logo: getEventLogoUrl(tournament),
        };
      })
      .filter(match => match !== null);

    return NextResponse.json(processedMatches);
  } catch (error) {
    console.error('Error fetching upcoming matches:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
