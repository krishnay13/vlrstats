const Database = require('./frontend/node_modules/better-sqlite3');
const db = new Database('./valorant_esports.db');

// Import the functions (simplified versions for testing)
function getRegionFromMatchName(matchName) {
  if (!matchName) return 'UNKNOWN';
  const name = matchName.toLowerCase();
  
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

function getTournamentSortPriority(tournament, stage) {
  const t = (tournament || '').toLowerCase();
  const s = (stage || '').toLowerCase();
  
  const yearMatch = tournament.match(/\b(202[0-9]|203[0-9])\b/);
  const year = yearMatch ? parseInt(yearMatch[1]) : 0;
  
  let tournamentPriority = 0;
  if (t.includes('champions') && !t.includes('champions tour')) {
    tournamentPriority = 6;
  } else if (t.includes('masters')) {
    tournamentPriority = 5;
  } else if (t.includes('champions tour') || t.includes('vct')) {
    tournamentPriority = 3;
  }
  
  let stagePriority = 0;
  if (s.includes('playoffs')) stagePriority = 5;
  else if (s.includes('grand final')) stagePriority = 6;
  else if (s.includes('stage 2')) stagePriority = 3;
  else if (s.includes('stage 1')) stagePriority = 2;
  else if (s.includes('kickoff')) stagePriority = 1;
  else if (s.includes('swiss')) stagePriority = 4;
  else if (s.includes('group stage')) stagePriority = 4;
  
  return { year, tournamentPriority, stagePriority };
}

function getRegionSortOrder(region) {
  const order = { AMERICAS: 1, EMEA: 2, APAC: 3, CHINA: 4, UNKNOWN: 5 };
  return order[region] || 99;
}

// Get all matches
const matches = db.prepare('SELECT * FROM Matches ORDER BY match_date DESC LIMIT 100').all();

// Process matches
const processed = matches.map(match => {
  const tournament = match.tournament || 'Unknown Event';
  const stage = match.stage || '';
  const matchName = match.match_name || '';
  const region = getRegionFromMatchName(matchName);
  const yearMatch = tournament.match(/\b(202[0-9]|203[0-9])\b/);
  const year = yearMatch ? parseInt(yearMatch[1]) : 0;
  
  let groupKey;
  if (tournament.includes('Valorant Champions') || tournament.includes('Masters')) {
    groupKey = tournament;
  } else {
    if (region !== 'UNKNOWN') {
      groupKey = `${tournament} - ${stage} - ${region}`;
    } else {
      groupKey = `${tournament} - ${stage}`;
    }
  }
  
  return { tournament, stage, region, year, groupKey };
});

// Group by groupKey
const grouped = {};
processed.forEach(match => {
  if (!grouped[match.groupKey]) {
    grouped[match.groupKey] = [];
  }
  grouped[match.groupKey].push(match);
});

// Sort
const sorted = Object.keys(grouped).sort((a, b) => {
  const matchA = grouped[a][0];
  const matchB = grouped[b][0];
  
  const priorityA = getTournamentSortPriority(matchA.tournament, matchA.stage);
  const priorityB = getTournamentSortPriority(matchB.tournament, matchB.stage);
  
  if (priorityA.year !== priorityB.year) {
    return priorityB.year - priorityA.year;
  }
  
  if (priorityA.tournamentPriority !== priorityB.tournamentPriority) {
    return priorityB.tournamentPriority - priorityA.tournamentPriority;
  }
  
  if (priorityA.stagePriority !== priorityB.stagePriority) {
    return priorityB.stagePriority - priorityA.stagePriority;
  }
  
  const regionOrderA = getRegionSortOrder(matchA.region);
  const regionOrderB = getRegionSortOrder(matchB.region);
  if (regionOrderA !== regionOrderB) {
    return regionOrderA - regionOrderB;
  }
  
  return a.localeCompare(b);
});

console.log('=== Sorted Tournament Groups ===');
sorted.forEach(key => {
  const match = grouped[key][0];
  console.log(`${key} (Year: ${match.year}, Tournament Priority: ${getTournamentSortPriority(match.tournament, match.stage).tournamentPriority}, Stage Priority: ${getTournamentSortPriority(match.tournament, match.stage).stagePriority}, Region: ${match.region})`);
});

db.close();
