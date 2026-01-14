// Shared helpers for team/player activity derived from Matches + Player_Stats

import { getMatchesDateMeta, getMatchDateExpr, getMatchDateNonEmptyWhere } from './schema.js';
import { normalizeTeamName } from '../team-utils.js';

// Build all known variants for certain teams (manual alias expansion)
function buildTeamVariants(normalizedTeamName) {
  const allVariants = [normalizedTeamName];
  const aliasMap = {
    'via kru esports': 'KRÜ Esports',
    'via kru': 'KRÜ Esports',
    'kru esports': 'KRÜ Esports',
    'kru': 'KRÜ Esports',
    'visa kru esports': 'KRÜ Esports',
    'visa kru': 'KRÜ Esports',
    'movistar koi': 'KOI',
    'movistar koi(koi)': 'KOI',
    'koi': 'KOI',
  };

  for (const [variant, canonical] of Object.entries(aliasMap)) {
    if (canonical === normalizedTeamName) {
      allVariants.push(variant);
    }
  }

  return allVariants;
}

// Get team's last match date (checking all aliases)
export function getTeamLastMatchDate(db, rawTeamName) {
  const normalizedTeamName = normalizeTeamName(rawTeamName);
  try {
    const variants = buildTeamVariants(normalizedTeamName);
    const dateMeta = getMatchesDateMeta(db);
    const dateExpr = getMatchDateExpr(dateMeta);
    const nonEmptyWhere = getMatchDateNonEmptyWhere(dateMeta);

    if (!dateExpr || !nonEmptyWhere) {
      return null;
    }

    const placeholders = variants.map(() => '?').join(',');
    const params = [...variants, ...variants];

    const sql = `
      SELECT MAX(${dateExpr}) as last_match_date
      FROM Matches
      WHERE (team_a IN (${placeholders}) OR team_b IN (${placeholders}))
      AND ${nonEmptyWhere}
    `;

    const result = db.prepare(sql).get(...params);
    return result?.last_match_date || null;
  } catch (e) {
    return null;
  }
}

// Get player's last match date
export function getPlayerLastMatchDate(db, playerName) {
  try {
    const dateMeta = getMatchesDateMeta(db);
    const dateExpr = getMatchDateExpr(dateMeta, 'm');
    const nonEmptyWhere = getMatchDateNonEmptyWhere(dateMeta, 'm');

    if (!dateExpr || !nonEmptyWhere) {
      return null;
    }

    // Get player's team from Player_Stats
    const playerTeam = db
      .prepare('SELECT DISTINCT team FROM Player_Stats WHERE player = ? LIMIT 1')
      .get(playerName);
    if (!playerTeam || !playerTeam.team) return null;

    const sql = `
      SELECT MAX(${dateExpr}) as last_match_date
      FROM Matches m
      WHERE (m.team_a = ? OR m.team_b = ?)
      AND ${nonEmptyWhere}
    `;

    const result = db.prepare(sql).get(playerTeam.team, playerTeam.team);
    if (result?.last_match_date) {
      return result.last_match_date;
    }
  } catch (e) {
    // fall through to alternative path
  }

  // Alternative: check Player_Stats -> Maps -> Matches directly
  try {
    const dateMeta = getMatchesDateMeta(db);
    const dateExpr = getMatchDateExpr(dateMeta, 'm');
    const nonEmptyWhere = getMatchDateNonEmptyWhere(dateMeta, 'm');

    if (!dateExpr || !nonEmptyWhere) {
      return null;
    }

    const sql = `
      SELECT MAX(${dateExpr}) as last_match_date
      FROM Player_Stats ps
      JOIN Maps mp ON ps.map_id = mp.id
      JOIN Matches m ON mp.match_id = m.match_id
      WHERE ps.player = ?
      AND ${nonEmptyWhere}
    `;

    const result = db.prepare(sql).get(playerName);
    return result?.last_match_date || null;
  } catch (e2) {
    return null;
  }
}

// Get all teams a player has played for (for backend storage)
export function getPlayerTeams(db, playerName) {
  try {
    const dateMeta = getMatchesDateMeta(db);
    const dateExpr = getMatchDateExpr(dateMeta, 'm');

    const hasDateExpr = !!dateExpr;

    if (hasDateExpr) {
      const sql = `
        SELECT DISTINCT 
          ps.team as team_name,
          MAX(${dateExpr}) as last_match_date
        FROM Player_Stats ps
        LEFT JOIN Maps mp ON ps.map_id = mp.id
        LEFT JOIN Matches m ON mp.match_id = m.match_id
        WHERE ps.player = ?
        AND ps.team IS NOT NULL AND ps.team != ''
        GROUP BY ps.team
        ORDER BY last_match_date DESC
      `;

      const teams = db.prepare(sql).all(playerName);
      return teams.map((t) => ({
        team_name: normalizeTeamName(t.team_name),
        last_match_date: t.last_match_date,
      }));
    }
  } catch (e) {
    // fall through to fallback
  }

  // Fallback: just get distinct teams
  try {
    const teams = db
      .prepare(
        `
        SELECT DISTINCT team as team_name
        FROM Player_Stats
        WHERE player = ? AND team IS NOT NULL AND team != ''
      `,
      )
      .all(playerName);
    return teams.map((t) => ({
      team_name: normalizeTeamName(t.team_name),
      last_match_date: null,
    }));
  } catch (e2) {
    return [];
  }
}

