// Helper function to determine region from tournament name
export function getRegionFromTournament(tournament) {
  if (!tournament) return 'UNKNOWN';
  const t = tournament.toLowerCase();
  
  // China/CN
  if (t.includes('china') || t.includes('chinese') || t.includes('cn ')) {
    return 'CHINA';
  }
  
  // APAC
  if (t.includes('pacific') || t.includes('apac') || t.includes('asia') || 
      t.includes('korea') || t.includes('japan') || t.includes('thailand') ||
      t.includes('philippines') || t.includes('indonesia') || t.includes('vietnam') ||
      t.includes('singapore') || t.includes('malaysia') || t.includes('oceania') ||
      t.includes('australia') || t.includes('hong kong') || t.includes('taiwan') ||
      t.includes('bangkok')) {
    return 'APAC';
  }
  
  // EMEA
  if (t.includes('emea') || t.includes('europe') || t.includes('mena') ||
      t.includes('turkey') || t.includes('cis') || t.includes('spain') ||
      t.includes('france') || t.includes('germany') || t.includes('uk') ||
      t.includes('poland') || t.includes('italy') || t.includes('portugal') ||
      t.includes('madrid')) {
    return 'EMEA';
  }
  
  // Americas
  if (t.includes('americas') || t.includes('north america') || t.includes('south america') ||
      t.includes('na ') || t.includes('latam') || t.includes('brazil') ||
      t.includes('argentina') || t.includes('chile') || t.includes('colombia') ||
      t.includes('mexico') || t.includes('peru') || t.includes('toronto')) {
    return 'AMERICAS';
  }
  
  return 'UNKNOWN';
}

// Helper function to determine region from team name (for fallback)
export function getRegionFromTeam(teamName) {
  if (!teamName) return 'UNKNOWN';
  const t = teamName.toLowerCase();
  
  // Known Americas teams
  const americasTeams = ['nrg', 'cloud9', 'c9', 'furia', 'loud', 'sentinels', '100 thieves', 
                         'leviatán', 'kru', 'kru esports', 'mibr', 'evil geniuses', 'eg',
                         'g2 esports', 'g2', 'luminosity', 'shopify rebellion', 'tsm',
                         'fur esports', '2g esports', '2game esports'];
  if (americasTeams.some(team => t.includes(team))) {
    return 'AMERICAS';
  }
  
  // Known EMEA teams
  const emeaTeams = ['fnatic', 'navi', 'natus vincere', 'team liquid', 'tl', 'vitality', 
                     'karmine corp', 'kc', 'bbl', 'fut', 'giants', 'bds', 'th', 'gentle mates',
                     'apeks'];
  if (emeaTeams.some(team => t.includes(team))) {
    return 'EMEA';
  }
  
  // Known APAC teams
  const apacTeams = ['zeta division', 'zeta', 't1', 'gen.g', 'geng', 'drx', 'talon', 
                     'team secret', 'global esports', 'paper rex', 'prx', 'bleed', 'rex regum qeon', 'rrq',
                     'boom esports', 'detonator', 'dfm', 'detonationfocusme', 'trace esports'];
  if (apacTeams.some(team => t.includes(team))) {
    return 'APAC';
  }
  
  // Known China teams
  const chinaTeams = ['edward gaming', 'edg', 'funplus phoenix', 'fpx', 'bilibili gaming', 'blg',
                      'dragon ranger gaming', 'jdg esports', 'nova esports', 'tec esports',
                      'wolves', 'xi lai gaming', 'all gamers'];
  if (chinaTeams.some(team => t.includes(team))) {
    return 'CHINA';
  }
  
  return 'UNKNOWN';
}

// Helper function to check if date is older than 6 months
export function isOlderThanSixMonths(dateString, timestampString) {
  const dateValue = dateString || timestampString;
  if (!dateValue) return false;
  
  try {
    let date;
    if (dateValue.includes('T') || dateValue.includes('Z')) {
      date = new Date(dateValue);
    } else if (dateValue.match(/^\d{4}-\d{2}-\d{2}/)) {
      date = new Date(dateValue);
    } else {
      date = new Date(dateValue);
    }
    
    if (isNaN(date.getTime())) {
      return false;
    }
    
    const sixMonthsAgo = new Date();
    sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
    return date < sixMonthsAgo;
  } catch (e) {
    return false;
  }
}

// Helper function to extract year from tournament name
export function getYearFromTournament(tournament) {
  if (!tournament) return 'Unknown';
  const yearMatch = tournament.match(/\b(202[0-9]|203[0-9])\b/);
  return yearMatch ? yearMatch[1] : 'Unknown';
}

// Helper function to extract region from match_name
export function getRegionFromMatchName(matchName) {
  if (!matchName) return 'UNKNOWN';
  const name = matchName.toLowerCase();
  
  // Check for region keywords in match name
  if (name.includes('americas') || name.includes('america kickoff') || name.includes('america stage')) {
    return 'AMERICAS';
  }
  if (name.includes('emea') || name.includes('emea kickoff') || name.includes('emea stage')) {
    return 'EMEA';
  }
  if (name.includes('china') || name.includes('chinese') || name.includes('china kickoff') || name.includes('china stage')) {
    return 'CHINA';
  }
  if (name.includes('pacific') || name.includes('apac') || name.includes('pacific kickoff') || name.includes('pacific stage')) {
    return 'APAC';
  }
  
  return 'UNKNOWN';
}

// Helper function to get tournament sort priority
// Ordered within a year as: Kickoff -> Stage 1 -> Stage 2 -> Masters -> Champions
// Playoffs / Swiss / Group Stage are NOT treated as separate buckets.
export function getTournamentSortPriority(tournament, stage) {
  const t = (tournament || '').toLowerCase();
  const s = (stage || '').toLowerCase();
  
  // Extract year
  const yearMatch = tournament.match(/\b(202[0-9]|203[0-9])\b/);
  const year = yearMatch ? parseInt(yearMatch[1]) : 0;
  
  // Overall order:
  // 1 = Kickoff
  // 2 = Stage 1
  // 3 = Stage 2
  // 4 = Masters
  // 5 = Champions
  let order = 0;

  const hasKickoff = t.includes('kickoff') || s.includes('kickoff');
  const hasStage1 = t.includes('stage 1') || s.includes('stage 1');
  const hasStage2 = t.includes('stage 2') || s.includes('stage 2');
  const isMasters = t.includes('masters');
  const isChampionsMainEvent = t.includes('champions') && !t.includes('champions tour');

  if (hasKickoff) {
    order = 1;
  } else if (hasStage1) {
    order = 2;
  } else if (hasStage2) {
    order = 3;
  } else if (isMasters) {
    order = 4;
  } else if (isChampionsMainEvent) {
    order = 5;
  }
  
  return {
    year,
    order,
    tournament: tournament || '',
    stage: stage || '',
  };
}

// Helper function to get region sort order
export function getRegionSortOrder(region) {
  const order = { AMERICAS: 1, EMEA: 2, APAC: 3, CHINA: 4, UNKNOWN: 5 };
  return order[region] || 99;
}

export function inferTeamRegion(db, teamName) {
  if (!teamName) return 'UNKNOWN';

  const normalized = teamName.toLowerCase().trim();
  
  // Known team regions database (from region-detector)
  const knownTeamRegions = {
    'nrg': 'AMERICAS', 'cloud9': 'AMERICAS', 'c9': 'AMERICAS', 'furia': 'AMERICAS',
    'furia esports': 'AMERICAS', '2g esports': 'AMERICAS', '2game esports': 'AMERICAS',
    'loud': 'AMERICAS', 'sentinels': 'AMERICAS', '100 thieves': 'AMERICAS',
    'leviatán': 'AMERICAS', 'leviatan': 'AMERICAS', 'kru': 'AMERICAS',
    'kru esports': 'AMERICAS', 'krü esports': 'AMERICAS', 'mibr': 'AMERICAS',
    'evil geniuses': 'AMERICAS', 'eg': 'AMERICAS', 'g2 esports': 'AMERICAS',
    'g2': 'AMERICAS', 'luminosity': 'AMERICAS', 'shopify rebellion': 'AMERICAS',
    'tsm': 'AMERICAS', 'moist moguls': 'AMERICAS', 'the guard': 'AMERICAS',
    'fnatic': 'EMEA', 'navi': 'EMEA', 'natus vincere': 'EMEA',
    'team liquid': 'EMEA', 'tl': 'EMEA', 'team vitality': 'EMEA', 'vitality': 'EMEA',
    'karmine corp': 'EMEA', 'kc': 'EMEA', 'bbl': 'EMEA', 'fut': 'EMEA', 'apeks': 'EMEA',
    'giants': 'EMEA', 'bds': 'EMEA', 'th': 'EMEA', 'team heretics': 'EMEA',
    'gentle mates': 'EMEA', 'koi': 'EMEA', 'movistar koi': 'EMEA',
    'giantx': 'EMEA', 'gx': 'EMEA',
    'zeta division': 'APAC', 'zeta': 'APAC', 't1': 'APAC',
    'gen.g': 'APAC', 'geng': 'APAC', 'global esports': 'APAC', 'drx': 'APAC', 'talon': 'APAC',
    'team secret': 'APAC', 'global esports': 'APAC', 'paper rex': 'APAC',
    'prx': 'APAC', 'bleed': 'APAC', 'rex regum qeon': 'APAC', 'rrq': 'APAC',
    'boom esports': 'APAC', 'detonation focusme': 'APAC', 'dfm': 'APAC',
    'nongshim redforce': 'APAC', 'trace esports': 'APAC', 'tec esports': 'CHINA',
    'edward gaming': 'CHINA', 'edg': 'CHINA', 'funplus phoenix': 'CHINA',
    'fpx': 'CHINA', 'bilibili gaming': 'CHINA', 'blg': 'CHINA', 'dragon ranger gaming': 'CHINA',
    'jdg esports': 'CHINA', 'nova esports': 'CHINA', 'wolves': 'CHINA', 'xi lai gaming': 'CHINA',
    'all gamers': 'CHINA',
  };
  
  // Check known teams first (normalized lookup)
  if (knownTeamRegions[normalized]) {
    return knownTeamRegions[normalized];
  }
  
  // Also check with canonical names that might come from database
  // Map canonical forms to lowercase keys for lookup
  const canonicalToLower = {
    '2g esports': '2g esports',
    'detonation focusme': 'detonation focusme',
    'karmine corp': 'karmine corp',
    'nongshim redforce': 'nongshim redforce',
    'team vitality': 'team vitality',
    'tec esports': 'tec esports',
    'furia esports': 'furia esports',
    'global esports': 'global esports',
  };
  
  const lowerKey = canonicalToLower[normalized] || normalized;
  if (knownTeamRegions[lowerKey]) {
    return knownTeamRegions[lowerKey];
  }
  
  // Check partial matches
  for (const [knownTeam, region] of Object.entries(knownTeamRegions)) {
    if (normalized.includes(knownTeam) || knownTeam.includes(normalized)) {
      return region;
    }
  }

  try {
    // First try to get region from match_name (more accurate)
    const matches = db
      .prepare(
        `
        SELECT DISTINCT match_name 
        FROM Matches 
        WHERE (team_a = ? OR team_b = ?)
        AND match_name IS NOT NULL 
        AND match_name != ''
        LIMIT 100
      `
      )
      .all(teamName, teamName);

    const regionCounts = { APAC: 0, CHINA: 0, EMEA: 0, AMERICAS: 0 };
    matches.forEach((m) => {
      const region = getRegionFromMatchName(m.match_name);
      if (region !== 'UNKNOWN') {
        regionCounts[region] = (regionCounts[region] || 0) + 1;
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

    // Fallback to tournament name
    const tournaments = db
      .prepare(
        `
        SELECT DISTINCT tournament 
        FROM Matches 
        WHERE (team_a = ? OR team_b = ?)
        AND tournament IS NOT NULL 
        AND tournament != ''
        LIMIT 50
      `
      )
      .all(teamName, teamName);

    tournaments.forEach((t) => {
      const region = getRegionFromTournament(t.tournament);
      if (region !== 'UNKNOWN') {
        regionCounts[region] = (regionCounts[region] || 0) + 1;
      }
    });

    const maxCount2 = Math.max(...Object.values(regionCounts));
    if (maxCount2 > 0) {
      for (const [region, count] of Object.entries(regionCounts)) {
        if (count === maxCount2) {
          return region;
        }
      }
    }
  } catch (e) {
    // fallback below
  }

  return getRegionFromTeam(teamName);
}
