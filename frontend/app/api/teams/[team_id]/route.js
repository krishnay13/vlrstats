// frontend/app/api/teams/[team_id]/route.js

import { NextResponse } from 'next/server';
import db from '@/app/lib/db.js';
import { inferTeamRegion, isOlderThanSixMonths } from '@/app/lib/region-utils.js';
import { normalizeTeamName, getTeamNameVariants } from '@/app/lib/team-utils.js';
import { getTeamLastMatchDate, buildTeamVariants } from '@/app/lib/db/activity.js';
import { getTeamLogoUrl } from '@/app/lib/logos.js';
import { getMatchesDateMeta, getMatchDateExpr, getMatchDateNonEmptyWhere } from '@/app/lib/db/schema.js';

export async function GET(request, { params }) {
  try {
    const { team_id } = params;
    const { searchParams } = new URL(request.url);
    const year = searchParams.get('year') || '2026'; // Default to 2026

    // team_id is the encoded team name from the teams list
    const decodedName = decodeURIComponent(team_id);
    const canonicalName = normalizeTeamName(decodedName);

    // Basic team metadata
    const region = inferTeamRegion(db, canonicalName);
    const lastMatchDate = getTeamLastMatchDate(db, canonicalName);
    const is_inactive = lastMatchDate ? isOlderThanSixMonths(lastMatchDate, null) : false;

    // Get all possible team name variants including aliases
    const allVariants = getTeamNameVariants(canonicalName);
    const variantsLower = allVariants.map(v => v.toLowerCase().trim());
    
    // Also get variants from the old method for backward compatibility
    const legacyVariants = buildTeamVariants(canonicalName);
    legacyVariants.forEach(v => {
      const lower = (v || '').toLowerCase().trim();
      if (lower && !variantsLower.includes(lower)) {
        variantsLower.push(lower);
      }
    });

    // Compute per-player last match date for this team (via Maps -> Matches)
    const dateMeta = getMatchesDateMeta(db);
    const dateExpr = getMatchDateExpr(dateMeta, 'm');
    const nonEmptyWhere = getMatchDateNonEmptyWhere(dateMeta, 'm');
    const hasDateMeta = !!(dateExpr && nonEmptyWhere);

    let activePlayers = [];
    let inactivePlayers = [];

    const placeholders = variantsLower.map(() => '?').join(',');
    // Need variants for both team matching (m.team_a/b) AND ps.team filtering
    const queryParams = [...variantsLower, ...variantsLower, ...variantsLower];

    let rows = [];
    if (hasDateMeta) {
      const sql = `
        SELECT 
          ps.player AS player_name,
          MAX(${dateExpr}) AS last_match_date
        FROM Player_Stats ps
        LEFT JOIN Maps mp ON ps.map_id = mp.id
        LEFT JOIN Matches m ON mp.match_id = m.match_id
        WHERE (LOWER(m.team_a) IN (${placeholders}) OR LOWER(m.team_b) IN (${placeholders}))
          AND LOWER(ps.team) IN (${placeholders})
          AND ps.player IS NOT NULL AND ps.player != ''
          AND ${nonEmptyWhere}
        GROUP BY ps.player
        ORDER BY last_match_date DESC, player_name
      `;

      rows = db.prepare(sql).all(...queryParams);
    }

    // Prefer the most recent series (match) that has player stats for this team in the selected year
    const latestMatch = db.prepare(
      `
      SELECT m.match_id
      FROM Player_Stats ps
      JOIN Maps mp ON ps.map_id = mp.id
      JOIN Matches m ON mp.match_id = m.match_id
      WHERE LOWER(ps.team) IN (${placeholders})
        AND ps.player IS NOT NULL AND ps.player != ''
        AND m.match_date >= ?
        AND m.match_date < ?
      ORDER BY m.match_id DESC
      LIMIT 1
    `,
    ).get(...variantsLower, `${year}-01-01`, `${parseInt(year) + 1}-01-01`);

    let currentRoster = [];
    if (latestMatch?.match_id) {
      // Get match date for display - use COALESCE to handle both possible date columns
      const matchDateRow = db.prepare(
        `SELECT COALESCE(match_date, substr(match_ts_utc, 1, 10), '') as match_date FROM Matches WHERE match_id = ?`
      ).get(latestMatch.match_id);
      const matchDate = matchDateRow?.match_date || null;

      // Fetch the first 5 distinct players from the most recent match for this team,
      // ordered by rowid to respect insertion order (index-based team assignment)
      const rosterRows = db.prepare(
        `
        SELECT DISTINCT ps.player AS player_name
        FROM Player_Stats ps
        JOIN Maps mp ON ps.map_id = mp.id
        WHERE mp.match_id = ?
          AND LOWER(ps.team) IN (${placeholders})
          AND ps.player IS NOT NULL 
          AND ps.player != ''
        ORDER BY ps.rowid
        LIMIT 5
      `,
      ).all(latestMatch.match_id, ...variantsLower);

      currentRoster = rosterRows.map((row) => ({
        player_name: row.player_name,
        last_match_date: matchDate,
      }));
    }

    if (currentRoster.length > 0) {
      activePlayers = currentRoster;
      inactivePlayers = [];
    }

    const team = {
      team_name: canonicalName,
      region,
      is_inactive,
      last_match_date: lastMatchDate,
      logo_url: getTeamLogoUrl(canonicalName, 'large'),
    };

    return NextResponse.json({ team, activePlayers, inactivePlayers });
  } catch (error) {
    console.error('Error fetching team details:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
