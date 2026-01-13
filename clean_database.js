// Script to clean and fix database issues
const Database = require('./frontend/node_modules/better-sqlite3');
const db = new Database('./valorant_esports.db');

console.log('=== Database Cleaning Script ===\n');

// 1. Fix Maps table: Set NULL scores to 0
console.log('1. Fixing NULL scores in Maps table...');
const nullScores = db.prepare(`
  UPDATE Maps 
  SET team_a_score = COALESCE(team_a_score, 0),
      team_b_score = COALESCE(team_b_score, 0)
  WHERE team_a_score IS NULL OR team_b_score IS NULL
`).run();
console.log(`   Updated ${nullScores.changes} maps with NULL scores`);

// 2. Check for maps with missing IDs (shouldn't happen, but check)
console.log('\n2. Checking for maps with missing IDs...');
const missingIds = db.prepare('SELECT COUNT(*) as count FROM Maps WHERE id IS NULL').get();
console.log(`   Maps with NULL id: ${missingIds.count}`);

// 3. Check for Player_Stats with invalid map_id references
console.log('\n3. Checking Player_Stats for invalid map_id references...');
const invalidMapRefs = db.prepare(`
  SELECT COUNT(*) as count 
  FROM Player_Stats ps
  LEFT JOIN Maps m ON ps.map_id = m.id
  WHERE ps.map_id IS NOT NULL AND m.id IS NULL
`).get();
console.log(`   Player_Stats with invalid map_id: ${invalidMapRefs.count}`);

// 4. Fix Player_Stats: Set map_id to NULL if it references non-existent map
if (invalidMapRefs.count > 0) {
  console.log('   Fixing invalid map_id references...');
  const fixed = db.prepare(`
    UPDATE Player_Stats
    SET map_id = NULL
    WHERE map_id IS NOT NULL 
    AND map_id NOT IN (SELECT id FROM Maps)
  `).run();
  console.log(`   Fixed ${fixed.changes} player stats records`);
}

// 5. Check for matches with missing team names
console.log('\n4. Checking for matches with missing team names...');
const missingTeams = db.prepare(`
  SELECT COUNT(*) as count 
  FROM Matches 
  WHERE (team_a IS NULL OR team_a = '') 
     OR (team_b IS NULL OR team_b = '')
`).get();
console.log(`   Matches with missing team names: ${missingTeams.count}`);

// 6. Check for maps with missing map names
console.log('\n5. Checking for maps with missing map names...');
const missingMapNames = db.prepare(`
  SELECT COUNT(*) as count 
  FROM Maps 
  WHERE map IS NULL OR map = ''
`).get();
console.log(`   Maps with missing map names: ${missingMapNames.count}`);

// 7. Check Player_Stats table structure
console.log('\n6. Checking Player_Stats table structure...');
try {
  const statsSchema = db.prepare('PRAGMA table_info(Player_Stats)').all();
  console.log(`   Player_Stats columns: ${statsSchema.map(c => c.name).join(', ')}`);
  
  // Check for Player_Stats with missing player references (if Players table exists)
  try {
    const missingPlayers = db.prepare(`
      SELECT COUNT(*) as count 
      FROM Player_Stats ps
      LEFT JOIN Players p ON ps.player_id = p.player_id
      WHERE ps.player_id IS NOT NULL AND p.player_id IS NULL
    `).get();
    console.log(`   Player_Stats with invalid player_id: ${missingPlayers.count}`);
  } catch (e) {
    console.log(`   Players table not found, skipping player reference check`);
  }
} catch (e) {
  console.log(`   Error checking Player_Stats: ${e.message}`);
}

// 8. Summary statistics
console.log('\n=== Summary ===');
const totalMatches = db.prepare('SELECT COUNT(*) as count FROM Matches').get();
const totalMaps = db.prepare('SELECT COUNT(*) as count FROM Maps').get();
const totalStats = db.prepare('SELECT COUNT(*) as count FROM Player_Stats').get();

console.log(`Total Matches: ${totalMatches.count}`);
console.log(`Total Maps: ${totalMaps.count}`);
console.log(`Total Player Stats: ${totalStats.count}`);

// Check what tables exist
const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all();
console.log(`\nTables in database: ${tables.map(t => t.name).join(', ')}`);

// 9. Show sample of cleaned data
console.log('\n=== Sample of cleaned Maps ===');
const sample = db.prepare('SELECT id, match_id, map, team_a_score, team_b_score FROM Maps WHERE team_a_score IS NOT NULL AND team_b_score IS NOT NULL LIMIT 5').all();
console.log(JSON.stringify(sample, null, 2));

db.close();
console.log('\n=== Database cleaning complete! ===');
