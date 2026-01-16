#!/usr/bin/env node
/**
 * List players missing team logos and teams with UNKNOWN region
 * (mirrors /api/players logic).
 */
import db from '../frontend/app/lib/db.js';
import regionPkg from '../frontend/app/lib/region-utils.js';
import teamPkg from '../frontend/app/lib/team-utils.js';
import activityPkg from '../frontend/app/lib/db/activity.js';
import logosPkg from '../frontend/app/lib/logos.js';

const { isOlderThanSixMonths, inferTeamRegion } = regionPkg;
const { isShowmatchTeam, normalizeTeamName } = teamPkg;
const { getPlayerLastMatchDate, getPlayerTeams } = activityPkg;
const { getTeamLogoUrl } = logosPkg;

function main() {
  // Fetch all player/team pairs
  const allRows = db.prepare(`
    SELECT DISTINCT ps.player AS player_name, ps.team AS team_name
    FROM Player_Stats ps
    WHERE ps.player IS NOT NULL AND ps.player != ''
    ORDER BY ps.player
  `).all();

  // Build players map like API
  const playersMap = new Map();
  for (const row of allRows) {
    const normalizedTeam = normalizeTeamName(row.team_name);
    if (isShowmatchTeam(normalizedTeam)) continue;
    if (!playersMap.has(row.player_name)) {
      playersMap.set(row.player_name, { player_name: row.player_name, teams: [] });
    }
    const player = playersMap.get(row.player_name);
    if (!player.teams.some((t) => t.team_name === normalizedTeam)) {
      player.teams.push({ team_name: normalizedTeam });
    }
  }

  const missingLogo = [];
  const missingRegionTeams = new Set();

  for (const player of playersMap.values()) {
    const allTeams = getPlayerTeams(db, player.player_name).filter((t) => !isShowmatchTeam(t.team_name));
    const mostRecentTeam = allTeams[0] || null; // already sorted desc
    const lastMatchDate = (mostRecentTeam && mostRecentTeam.last_match_date) || getPlayerLastMatchDate(db, player.player_name);
    const isInactive = lastMatchDate ? isOlderThanSixMonths(lastMatchDate, null) : false;

    if (!mostRecentTeam) {
      // Free agent/unassigned
      missingLogo.push({ player: player.player_name, team: null, inactive: isInactive });
      missingRegionTeams.add('UNKNOWN');
      continue;
    }

    const teamName = mostRecentTeam.team_name;
    const logo = getTeamLogoUrl(teamName, 'small');
    const region = inferTeamRegion(db, teamName);

    if (!logo) {
      missingLogo.push({ player: player.player_name, team: teamName, inactive: isInactive });
    }
    if (!region || region === 'UNKNOWN') {
      missingRegionTeams.add(teamName);
    }
  }

  console.log('Players missing team logo:', missingLogo.length);
  for (const entry of missingLogo) {
    console.log(`- ${entry.player} ${entry.team ? `(${entry.team})` : '(no team)'}`);
  }

  console.log('\nTeams with UNKNOWN region:', missingRegionTeams.size);
  for (const team of Array.from(missingRegionTeams).sort()) {
    console.log(`- ${team}`);
  }
}

main();
