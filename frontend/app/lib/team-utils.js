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
  'mkoi': 'KOI',

  // Core teams
  '100t': '100 Thieves',
  '100 thieves': '100 Thieves',
  'c9': 'Cloud9',
  'cloud9': 'Cloud9',
  'drx': 'DRX',
  'g2': 'G2 Esports',
  'ge': 'Global Esports',
  'gening esports': 'Gen.G',
  'genG': 'Gen.G',
  'gen.g': 'Gen.G',
  'gen': 'Gen.G',
  'geng': 'Gen.G',
  'global esports': 'Global Esports',
  'globalesports': 'Global Esports',
  'gx': 'GIANTX',
  'loud': 'LOUD',
  'mibr': 'MIBR',
  'nrg': 'NRG',
  't1': 'T1',
  'tl': 'Team Liquid',

  // Full names
  'fnc': 'FNATIC',
  'fnatic': 'FNATIC',
  'rrq': 'Rex Regum Qeon',
  'rex regum qeon': 'Rex Regum Qeon',
  'prx': 'Paper Rex',
  'paper rex': 'Paper Rex',
  'edg': 'EDward Gaming',
  'edward gaming': 'EDward Gaming',
  'xlg': 'Xi Lai Gaming',
  'xi lai gaming': 'Xi Lai Gaming',
  'th': 'Team Heretics',
  'team heretics': 'Team Heretics',
  'sen': 'Sentinels',
  'sentinels': 'Sentinels',

  // Regional/International teams
  '2g': '2G Esports',
  '2g esports': '2G Esports',
  '2game esports': '2G Esports',
  '2game_esports': '2G Esports',
  'ag': 'All Gamers',
  'all gamers': 'All Gamers',
  'apk': 'Apeks',
  'apeks': 'Apeks',
  'bbl': 'BBL Esports',
  'bbl esports': 'BBL Esports',
  'bld': 'Bleed Esports',
  'bleed': 'Bleed Esports',
  'bleed esports': 'Bleed Esports',
  'bme': 'BOOM Esports',
  'boom esports': 'BOOM Esports',
  'dfm': 'DetonatioN FocusMe',
  'detonator': 'DetonatioN FocusMe',
  'detonationfocusme': 'DetonatioN FocusMe',
  'detonation focusme': 'DetonatioN FocusMe',
  'detonationfocus': 'DetonatioN FocusMe',
  'drg': 'Dragon Ranger Gaming',
  'dragon ranger gaming': 'Dragon Ranger Gaming',
  'eg': 'Evil Geniuses',
  'evil geniuses': 'Evil Geniuses',
  'fpx': 'FunPlus Phoenix',
  'funplus phoenix': 'FunPlus Phoenix',
  'fur': 'Furia Esports',
  'fur esports': 'Furia Esports',
  'furia': 'Furia Esports',
  'furia esports': 'Furia Esports',
  'fut': 'FUT Esports',
  'fut esports': 'FUT Esports',
  'kc': 'Karmine Corp',
  'karmine corp': 'Karmine Corp',
  'karminecorp': 'Karmine Corp',
  'karmine': 'Karmine Corp',
  'krü': 'KRÜ Esports',
  'kru esports': 'KRÜ Esports',
  'lev': 'Leviatan',
  'leviatan': 'Leviatan',
  'm8': 'Gentle Mates',
  'gentle mates': 'Gentle Mates',
  'gentle m8tes': 'Gentle Mates',
  'navi': 'Natus Vincere',
  'natus vincere': 'Natus Vincere',
  'nova': 'Nova Esports',
  'nova esports': 'Nova Esports',
  'ns': 'Nongshim Redforce',
  'nongshim': 'Nongshim Redforce',
  'nsr': 'Nongshim Redforce',
  'nongshim redforce': 'Nongshim Redforce',
  'nsredforce': 'Nongshim Redforce',
  'ns redforce': 'Nongshim Redforce',
  'nongshimredforce': 'Nongshim Redforce',
  'nongshim esports': 'Nongshim Redforce',
  'te': 'Trace Esports',
  'trace esports': 'Trace Esports',
  'tec': 'TEC Esports',
  'tec esports': 'TEC Esports',
  'titan esports club': 'TEC Esports',
  'titan_esports_club_2025': 'TEC Esports',
  'tln': 'Talon Esports',
  'talon': 'Talon Esports',
  'talon esports': 'Talon Esports',
  'ts': 'Team Secret',
  'team secret': 'Team Secret',
  'tyl': 'Talon Esports',
  'vit': 'Team Vitality',
  'vitality': 'Team Vitality',
  'team vitality': 'Team Vitality',
  'wol': 'Wolves',
  'wolves': 'Wolves',
  '2game_esports': '2G Esports',
  '2game esports': '2G Esports',
  'zeta': 'ZETA DIVISION',
  'zeta division': 'ZETA DIVISION',
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
 * Get all possible name variants for a team (includes aliases and canonical)
 * @param {string} canonicalName - The canonical team name
 * @returns {string[]} - Array of all possible variants (lowercase)
 */
export function getTeamNameVariants(canonicalName) {
  const variants = new Set();
  const canonical = normalizeTeamName(canonicalName);
  
  // Add the canonical name
  variants.add(canonical.toLowerCase().trim());
  
  // Add the original name (in case it's not an alias key)
  variants.add(canonicalName.toLowerCase().trim());
  
  // Find all alias keys that map to this canonical name
  for (const [aliasKey, aliasValue] of Object.entries(TEAM_ALIASES)) {
    if (aliasValue.toLowerCase().trim() === canonical.toLowerCase().trim()) {
      variants.add(aliasKey.toLowerCase().trim());
    }
  }
  
  return Array.from(variants);
}

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
