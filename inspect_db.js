const Database = require('./frontend/node_modules/better-sqlite3');
const db = new Database('./valorant_esports.db');

console.log('=== Sample Kickoff matches ===');
const kickoff = db.prepare('SELECT tournament, stage, match_name FROM Matches WHERE tournament = ? AND stage = ? LIMIT 3').all('Champions Tour 2024', 'Kickoff');
console.log(JSON.stringify(kickoff, null, 2));

console.log('\n=== Sample Stage 1 matches ===');
const stage1 = db.prepare('SELECT tournament, stage, match_name FROM Matches WHERE tournament = ? AND stage = ? LIMIT 3').all('Champions Tour 2024', 'Stage 1');
console.log(JSON.stringify(stage1, null, 2));

db.close();
