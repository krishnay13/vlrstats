const Database = require('./frontend/node_modules/better-sqlite3');
const db = new Database('./valorant_esports.db');

console.log('=== Checking Maps table schema ===');
const schema = db.prepare('PRAGMA table_info(Maps)').all();
console.log('Columns:', schema.map(c => ({name: c.name, type: c.type})));

console.log('\n=== Sample maps ===');
const sample = db.prepare('SELECT * FROM Maps LIMIT 3').all();
console.log(JSON.stringify(sample, null, 2));

console.log('\n=== Maps with missing scores ===');
const missingScores = db.prepare('SELECT id, match_id, map, team_a_score, team_b_score FROM Maps WHERE team_a_score IS NULL OR team_b_score IS NULL LIMIT 10').all();
console.log(JSON.stringify(missingScores, null, 2));

console.log('\n=== Maps with NULL id ===');
const nullIds = db.prepare('SELECT * FROM Maps WHERE id IS NULL LIMIT 5').all();
console.log('Count:', nullIds.length);

console.log('\n=== Total maps ===');
const total = db.prepare('SELECT COUNT(*) as count FROM Maps').get();
console.log('Total maps:', total.count);

db.close();
