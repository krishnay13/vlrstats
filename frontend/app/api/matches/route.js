// frontend/app/api/matches/route.js

import { NextResponse } from 'next/server';
import db from '@/app/lib/db.js';
import { getTournamentSortPriority } from '@/app/lib/region-utils.js';

// Helper function to check if team is a showmatch team
function isShowmatchTeam(teamName) {
  if (!teamName) return false;
  const name = teamName.toLowerCase();
  return name.includes('team international') || 
         name.includes('team spain') || 
         name.includes('team china') ||
         (name.includes('team ') && (name.includes('showmatch') || name.includes('all-star')));
}

export async function GET() {
  try {
    // Check which date columns exist
    const tableInfo = db.prepare("PRAGMA table_info(Matches)").all();
    const columns = tableInfo.map(col => col.name);
    const hasMatchDate = columns.includes('match_date');
    const hasMatchTsUtc = columns.includes('match_ts_utc');
    
    // Fetch all matches - use available date column for sorting
    let matches;
    if (hasMatchDate && hasMatchTsUtc) {
      matches = db.prepare(`
        SELECT * FROM Matches 
        ORDER BY COALESCE(match_date, substr(match_ts_utc, 1, 10), '') DESC, match_id DESC
      `).all();
    } else if (hasMatchTsUtc) {
      matches = db.prepare(`
        SELECT * FROM Matches 
        ORDER BY match_ts_utc DESC, match_id DESC
      `).all();
    } else if (hasMatchDate) {
      matches = db.prepare(`
        SELECT * FROM Matches 
        ORDER BY match_date DESC, match_id DESC
      `).all();
    } else {
      matches = db.prepare('SELECT * FROM Matches ORDER BY match_id DESC').all();
    }
    
    // Filter out showmatch teams and process matches
    const processedMatches = matches
      .map(match => {
        // Handle both naming conventions
        const team1 = match.team_a || match.team1_name;
        const team2 = match.team_b || match.team2_name;
        
        // Filter out matches with showmatch teams
        if (isShowmatchTeam(team1) || isShowmatchTeam(team2)) {
          return null;
        }
        
        const tournament = match.tournament || 'Unknown Event';
        const stage = match.stage || '';
        
        // Create a unique key for grouping: tournament + stage (if stage is meaningful)
        const groupKey = stage && !stage.toLowerCase().includes('showmatch') 
          ? `${tournament} - ${stage}`
          : tournament;
        
        return {
          ...match,
          tournament,
          stage,
          groupKey,
          team1_name: team1,
          team2_name: team2,
          team1_score: match.team_a_score || match.team1_score,
          team2_score: match.team_b_score || match.team2_score,
        };
      })
      .filter(match => match !== null);
    
    // Group by tournament + stage
    const grouped = {};
    processedMatches.forEach(match => {
      const key = match.groupKey;
      if (!grouped[key]) {
        grouped[key] = [];
      }
      grouped[key].push(match);
    });
    
    // Sort tournaments by priority
    const sortedTournaments = Object.keys(grouped).sort((a, b) => {
      // Get the first match from each group to extract tournament/stage info
      const matchA = grouped[a][0];
      const matchB = grouped[b][0];
      
      const priorityA = getTournamentSortPriority(matchA.tournament, matchA.stage);
      const priorityB = getTournamentSortPriority(matchB.tournament, matchB.stage);
      
      // Sort by year (newer first)
      if (priorityA.year !== priorityB.year) {
        return priorityB.year - priorityA.year;
      }
      
      // Sort by tournament priority (higher first)
      if (priorityA.tournamentPriority !== priorityB.tournamentPriority) {
        return priorityB.tournamentPriority - priorityA.tournamentPriority;
      }
      
      // Sort by stage priority (higher first)
      if (priorityA.stagePriority !== priorityB.stagePriority) {
        return priorityB.stagePriority - priorityA.stagePriority;
      }
      
      // Finally alphabetical
      return a.localeCompare(b);
    });
    
    // Rebuild grouped object with sorted tournaments
    const sortedGrouped = {};
    sortedTournaments.forEach(tournament => {
      sortedGrouped[tournament] = grouped[tournament];
    });
    
    return NextResponse.json({
      matches: processedMatches,
      grouped: sortedGrouped,
    });
  } catch (error) {
    console.error('Error fetching matches:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
