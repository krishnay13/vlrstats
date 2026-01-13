// Enhanced region detection using tournament analysis and OpenAI

import { getRegionFromTournament, getRegionFromMatchName } from './region-utils.js';

// Known team regions (comprehensive list from VCT tournaments)
const KNOWN_TEAM_REGIONS = {
  // Americas
  'nrg': 'AMERICAS',
  'cloud9': 'AMERICAS',
  'c9': 'AMERICAS',
  'furia': 'AMERICAS',
  'loud': 'AMERICAS',
  'sentinels': 'AMERICAS',
  '100 thieves': 'AMERICAS',
  'leviatán': 'AMERICAS',
  'leviatan': 'AMERICAS',
  'kru': 'AMERICAS',
  'kru esports': 'AMERICAS',
  'krü esports': 'AMERICAS',
  'mibr': 'AMERICAS',
  'evil geniuses': 'AMERICAS',
  'eg': 'AMERICAS',
  'g2 esports': 'AMERICAS',
  'g2': 'AMERICAS',
  'luminosity': 'AMERICAS',
  'shopify rebellion': 'AMERICAS',
  'tsm': 'AMERICAS',
  'moist moguls': 'AMERICAS',
  'the guard': 'AMERICAS',
  'ghost gaming': 'AMERICAS',
  'complexity': 'AMERICAS',
  'col': 'AMERICAS',
  
  // EMEA
  'fnatic': 'EMEA',
  'navi': 'EMEA',
  'natus vincere': 'EMEA',
  'team liquid': 'EMEA',
  'tl': 'EMEA',
  'vitality': 'EMEA',
  'karmine corp': 'EMEA',
  'kc': 'EMEA',
  'bbl': 'EMEA',
  'fut': 'EMEA',
  'giants': 'EMEA',
  'bds': 'EMEA',
  'th': 'EMEA',
  'team heretics': 'EMEA',
  'gentle mates': 'EMEA',
  'koi': 'EMEA',
  'movistar koi': 'EMEA',
  'giantx': 'EMEA',
  'gx': 'EMEA',
  'futbolist': 'EMEA',
  'fut': 'EMEA',
  'fenerbahçe': 'EMEA',
  'fenerbahce': 'EMEA',
  'bbl esports': 'EMEA',
  'bbl': 'EMEA',
  
  // APAC
  'zeta division': 'APAC',
  'zeta': 'APAC',
  't1': 'APAC',
  'gen.g': 'APAC',
  'geng': 'APAC',
  'drx': 'APAC',
  'talon': 'APAC',
  'team secret': 'APAC',
  'global esports': 'APAC',
  'paper rex': 'APAC',
  'prx': 'APAC',
  'bleed': 'APAC',
  'rex regum qeon': 'APAC',
  'rrq': 'APAC',
  'detonation focusme': 'APAC',
  'dfm': 'APAC',
  'scarz': 'APAC',
  'full sense': 'APAC',
  'xerxia': 'APAC',
  'xerxia esports': 'APAC',
  'boom esports': 'APAC',
  'boom': 'APAC',
  'on sla2ers': 'APAC',
  'sengoku gaming': 'APAC',
  'fennel': 'APAC',
  'genesis': 'APAC',
  
  // China
  'edward gaming': 'CHINA',
  'edg': 'CHINA',
  'funplus phoenix': 'CHINA',
  'fpx': 'CHINA',
  'bilibili gaming': 'CHINA',
  'blg': 'CHINA',
  'titan esports': 'CHINA',
  'titan': 'CHINA',
  'nova esports': 'CHINA',
  'nova': 'CHINA',
  'jdg esports': 'CHINA',
  'jdg': 'CHINA',
  'xi lai gaming': 'CHINA',
  'xlg': 'CHINA',
  'trace esports': 'CHINA',
  'trace': 'CHINA',
};

/**
 * Enhanced region detection for teams
 * Uses tournament analysis, match name analysis, and known team database
 */
export function detectTeamRegion(db, teamName) {
  if (!teamName) return 'UNKNOWN';
  
  const normalized = teamName.toLowerCase().trim();
  
  // First check known teams database
  if (KNOWN_TEAM_REGIONS[normalized]) {
    return KNOWN_TEAM_REGIONS[normalized];
  }
  
  // Check partial matches in known teams
  for (const [knownTeam, region] of Object.entries(KNOWN_TEAM_REGIONS)) {
    if (normalized.includes(knownTeam) || knownTeam.includes(normalized)) {
      return region;
    }
  }
  
  // Analyze tournaments the team has played in
  try {
    const tournaments = db.prepare(`
      SELECT DISTINCT tournament, match_name
      FROM Matches 
      WHERE (team_a = ? OR team_b = ?)
      AND tournament IS NOT NULL 
      AND tournament != ''
      LIMIT 50
    `).all(teamName, teamName);
    
    const regionCounts = { APAC: 0, CHINA: 0, EMEA: 0, AMERICAS: 0 };
    
    tournaments.forEach((row) => {
      // Check tournament name
      const tournamentRegion = getRegionFromTournament(row.tournament);
      if (tournamentRegion !== 'UNKNOWN') {
        regionCounts[tournamentRegion] = (regionCounts[tournamentRegion] || 0) + 1;
      }
      
      // Check match name
      if (row.match_name) {
        const matchRegion = getRegionFromMatchName(row.match_name);
        if (matchRegion !== 'UNKNOWN') {
          regionCounts[matchRegion] = (regionCounts[matchRegion] || 0) + 1;
        }
      }
    });
    
    const maxCount = Math.max(...Object.values(regionCounts));
    if (maxCount > 0) {
      for (const [region, count] of Object.entries(regionCounts)) {
        if (count === maxCount) {
          return region;
        }
      }
    }
  } catch (e) {
    // Fallback below
  }
  
  return 'UNKNOWN';
}
