// frontend/app/api/teams/[team_id]/route.js

import { NextResponse } from 'next/server';
import db from '@/app/lib/db.js';
import { inferTeamRegion, isOlderThanSixMonths } from '@/app/lib/region-utils.js';
import { normalizeTeamName } from '@/app/lib/team-utils.js';
import { getTeamLastMatchDate, buildTeamVariants } from '@/app/lib/db/activity.js';
import { getMatchesDateMeta, getMatchDateExpr, getMatchDateNonEmptyWhere } from '@/app/lib/db/schema.js';

export async function GET(request, { params }) {
  try {
    const { team_id } = params;

    // team_id is the encoded team name from the teams list
    const decodedName = decodeURIComponent(team_id);
    const canonicalName = normalizeTeamName(decodedName);

    // Basic team metadata
    const region = inferTeamRegion(db, canonicalName);
    const lastMatchDate = getTeamLastMatchDate(db, canonicalName);
    const is_inactive = lastMatchDate ? isOlderThanSixMonths(lastMatchDate, null) : false;

    // Build variants for this team so we pick up all alias spellings from Player_Stats
    const variants = buildTeamVariants(canonicalName);
    const variantsLower = variants.map((team) => (team || '').toLowerCase().trim());

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

    // Prefer the most recent series (match) that has player stats for this team
    const latestMatch = hasDateMeta
      ? db.prepare(
        `
        SELECT m.match_id, MAX(${dateExpr}) as match_date
        FROM Player_Stats ps
        JOIN Maps mp ON ps.map_id = mp.id
        JOIN Matches m ON mp.match_id = m.match_id
        WHERE LOWER(ps.team) IN (${placeholders})
          AND (LOWER(m.team_a) IN (${placeholders}) OR LOWER(m.team_b) IN (${placeholders}))
          AND ps.player IS NOT NULL AND ps.player != ''
          AND ${nonEmptyWhere}
        GROUP BY m.match_id
        ORDER BY match_date DESC
        LIMIT 1
      `,
      ).get(...queryParams)
      : db.prepare(
        `
        SELECT m.match_id
        FROM Player_Stats ps
        JOIN Maps mp ON ps.map_id = mp.id
        JOIN Matches m ON mp.match_id = m.match_id
        WHERE LOWER(ps.team) IN (${placeholders})
          AND (LOWER(m.team_a) IN (${placeholders}) OR LOWER(m.team_b) IN (${placeholders}))
          AND ps.player IS NOT NULL AND ps.player != ''
        ORDER BY m.match_id DESC
        LIMIT 1
      `,
      ).get(...queryParams);

    let currentRoster = [];
    if (latestMatch?.match_id) {
      const rosterRows = db.prepare(
        `
        SELECT DISTINCT ps.player AS player_name
        FROM Player_Stats ps
        JOIN Maps mp ON ps.map_id = mp.id
        WHERE mp.match_id = ?
          AND LOWER(ps.team) IN (${placeholders})
          AND ps.player IS NOT NULL AND ps.player != ''
        ORDER BY ps.player
      `,
      ).all(latestMatch.match_id, ...variantsLower);

      currentRoster = rosterRows.map((row) => ({
        player_name: row.player_name,
        last_match_date: latestMatch.match_date || null,
      }));
    }

    if (currentRoster.length > 0) {
      const activeNames = new Set(
        currentRoster.map((p) => (p.player_name || '').toLowerCase().trim()),
      );
      activePlayers = currentRoster;

      if (hasDateMeta) {
        inactivePlayers = rows
          .filter((row) => !activeNames.has((row.player_name || '').toLowerCase().trim()))
          .map((row) => ({
            player_name: row.player_name,
            last_match_date: row.last_match_date,
          }));
      } else {
        const allPlayers = db.prepare(
          `
          SELECT DISTINCT ps.player AS player_name
          FROM Player_Stats ps
          JOIN Maps mp ON ps.map_id = mp.id
          JOIN Matches m ON mp.match_id = m.match_id
          WHERE LOWER(ps.team) IN (${placeholders})
            AND (LOWER(m.team_a) IN (${placeholders}) OR LOWER(m.team_b) IN (${placeholders}))
            AND ps.player IS NOT NULL AND ps.player != ''
          ORDER BY ps.player
        `,
        ).all(...queryParams);

        inactivePlayers = allPlayers
          .filter((row) => !activeNames.has((row.player_name || '').toLowerCase().trim()))
          .map((row) => ({
            player_name: row.player_name,
            last_match_date: null,
          }));
      }
    } else if (hasDateMeta) {
      rows.forEach((row) => {
        const inactive = isOlderThanSixMonths(row.last_match_date, null);
        const player = {
          player_name: row.player_name,
          last_match_date: row.last_match_date,
        };
        if (inactive) {
          inactivePlayers.push(player);
        } else {
          activePlayers.push(player);
        }
      });
    }

    const team = {
      team_name: canonicalName,
      region,
      is_inactive,
      last_match_date: lastMatchDate,
    };

    return NextResponse.json({ team, activePlayers, inactivePlayers });
  } catch (error) {
    console.error('Error fetching team details:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
