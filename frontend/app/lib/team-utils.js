// Team normalization and filtering utilities

// Team aliases mapping (variant -> canonical)
// NOTE: This should be kept in sync with Python-side aliases (loadDB/aliases/teams.json)
// The canonical source is loadDB/aliases/teams.json - update this file when that changes
// TODO: Consider auto-generating this from loadDB/aliases/teams.json or sharing the JSON file
const TEAM_ALIASES = {
  // Bilibili / BLG variants
  'guangzhou huadu bilibili gaming(bilibili gaming)': 'Bilibili Gaming',
  'guangzhou huadu bilibili gaming': 'Bilibili Gaming',
  'bilibili gaming': 'Bilibili Gaming',
  'blg': 'Bilibili Gaming',

  // JDG variants
  'jd mall jdg esports(jdg esports)': 'JDG Esports',
  'jd mall jdg esports': 'JDG Esports',
  'jdg esports': 'JDG Esports',
  'jdg': 'JDG Esports',

  // KRU Esports variants
  'kru': 'KRÜ Esports',
  'kru esports': 'KRÜ Esports',
  'visa kru': 'KRÜ Esports',
  'visa kru esports': 'KRÜ Esports',
  'visa krü(krü esports)': 'KRÜ Esports',
  'via kru esports': 'KRÜ Esports',
  'via kru': 'KRÜ Esports',

  // Movistar KOI / KOI variants
  'movistar koi(koi)': 'KOI',
  'movistar koi': 'KOI',
  'koi': 'KOI',

  // Other known aliases / shorthands
  'g2': 'G2 Esports',
  'tl': 'Team Liquid',
  'fnc': 'FNATIC',
  't1': 'T1',
  'sen': 'Sentinels',
  'rrq': 'Rex Regum Qeon',
  'prx': 'Paper Rex',
  'edg': 'EDward Gaming',
  'drx': 'DRX',
  'mibr': 'MIBR',
  'xlg': 'Xi Lai Gaming',
  'th': 'Team Heretics',
  'gx': 'GIANTX',
  'nrg': 'NRG',
  'loud': 'LOUD',
  
  // Additional team abbreviations from players list
  '2g': '2G Esports',
  'ag': 'All Gamers',
  'apk': 'Apeks',
  'bbl': 'BBL Esports',
  'bld': 'Bleed Esports',
  'bme': 'BOOM Esports',
  'drg': 'Dragon Ranger Gaming',
  'm8': 'Gentle Mates',
  'gentle mates': 'Gentle Mates',
  'gentle m8tes': 'Gentle Mates',
  'nova': 'Nova Esports',
  'ns': 'Nongshim Esports',
  'nongshim': 'Nongshim Esports',
  'nsr': 'Nongshim Esports',
  'te': 'Trace Esports',
  'tec': 'TEC Esports',
  'titan esports club': 'Titan Esports Club',
  'tln': 'Talon Esports',
  'talon': 'Talon Esports',
  'ts': 'Team Secret',
  'team secret': 'Team Secret',
  'wol': 'Wolves',
  'wolves': 'Wolves',
};

// Showmatch teams to filter out
const SHOWMATCH_TEAMS = [
  'team international',
  'team spain',
  'team china',
  'team tarik',
  'team thailand',
  'team world',
  'glory once again',
  'team emea',
  'team france',
  'team toast',
  'team alpha',
  'team omega',
  'pure aim',
  'precise defeat',
];

/**
 * Normalize a team name using aliases
 * @param {string} teamName - The team name to normalize
 * @returns {string} - The normalized/canonical team name
 */
export function normalizeTeamName(teamName) {
  if (!teamName) return teamName;
  const normalized = teamName.toLowerCase().trim();
  return TEAM_ALIASES[normalized] || teamName;
}

/**
 * Check if a team is a showmatch team
 * @param {string} teamName - The team name to check
 * @returns {boolean} - True if it's a showmatch team
 */
export function isShowmatchTeam(teamName) {
  if (!teamName) return false;
  const name = teamName.toLowerCase().trim();
  
  // Check exact matches
  if (SHOWMATCH_TEAMS.includes(name)) {
    return true;
  }
  
  // Check for "team " prefix with showmatch indicators
  if (name.includes('team ') && (
    name.includes('showmatch') || 
    name.includes('all-star') ||
    name.includes('international') ||
    name.includes('spain') ||
    name.includes('china') ||
    name.includes('tarik') ||
    name.includes('thailand') ||
    name.includes('world') ||
    name.includes('emea') ||
    name.includes('france') ||
    name.includes('toast') ||
    name.includes('alpha') ||
    name.includes('omega')
  )) {
    return true;
  }
  
  // Check for "glory once again"
  if (name.includes('glory once again')) {
    return true;
  }
  
  return false;
}
