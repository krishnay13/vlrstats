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
                         'g2 esports', 'g2', 'luminosity', 'shopify rebellion', 'tsm'];
  if (americasTeams.some(team => t.includes(team))) {
    return 'AMERICAS';
  }
  
  // Known EMEA teams
  const emeaTeams = ['fnatic', 'navi', 'natus vincere', 'team liquid', 'tl', 'vitality', 
                     'karmine corp', 'kc', 'bbl', 'fut', 'giants', 'bds', 'th', 'gentle mates'];
  if (emeaTeams.some(team => t.includes(team))) {
    return 'EMEA';
  }
  
  // Known APAC teams
  const apacTeams = ['zeta division', 'zeta', 't1', 'gen.g', 'geng', 'drx', 'talon', 
                     'team secret', 'global esports', 'paper rex', 'prx', 'bleed', 'rex regum qeon', 'rrq'];
  if (apacTeams.some(team => t.includes(team))) {
    return 'APAC';
  }
  
  // Known China teams
  const chinaTeams = ['edward gaming', 'edg', 'funplus phoenix', 'fpx', 'bilibili gaming', 'blg'];
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

// Helper function to get tournament sort priority
export function getTournamentSortPriority(tournament, stage) {
  const t = (tournament || '').toLowerCase();
  const s = (stage || '').toLowerCase();
  
  // Extract year
  const yearMatch = tournament.match(/\b(202[0-9]|203[0-9])\b/);
  const year = yearMatch ? parseInt(yearMatch[1]) : 0;
  
  // Tournament type priority (higher = more important)
  let tournamentPriority = 0;
  if (t.includes('champions')) tournamentPriority = 5;
  else if (t.includes('masters')) tournamentPriority = 4;
  else if (t.includes('vct')) tournamentPriority = 3;
  else if (t.includes('champions tour')) tournamentPriority = 2;
  
  // Stage priority
  let stagePriority = 0;
  if (s.includes('playoffs')) stagePriority = 5;
  else if (s.includes('grand final')) stagePriority = 6;
  else if (s.includes('stage 2')) stagePriority = 3;
  else if (s.includes('stage 1')) stagePriority = 2;
  else if (s.includes('kickoff')) stagePriority = 1;
  else if (s.includes('swiss')) stagePriority = 4;
  else if (s.includes('group stage')) stagePriority = 4;
  
  return {
    year,
    tournamentPriority,
    stagePriority,
    tournament: tournament || '',
    stage: stage || '',
  };
}
