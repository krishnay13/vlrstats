"""
Test script to randomly sample and verify match data quality.
"""
import sqlite3
import random
from .db_utils import get_conn


def test_random_matches(num_samples: int = 10):
    """Test random matches from the database."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Get total count
    cur.execute("SELECT COUNT(*) FROM Matches")
    total = cur.fetchone()[0]
    
    if total == 0:
        print("No matches found in database!")
        return
    
    print(f"Total matches in database: {total}")
    print(f"Testing {min(num_samples, total)} random matches...\n")
    
    # Get random match IDs
    cur.execute("SELECT match_id FROM Matches ORDER BY RANDOM() LIMIT ?", (num_samples,))
    match_ids = [row[0] for row in cur.fetchall()]
    
    issues = []
    
    for match_id in match_ids:
        print(f"{'='*70}")
        print(f"Match ID: {match_id}")
        print(f"{'='*70}")
        
        # Get match info
        cur.execute("""
            SELECT match_id, tournament, stage, match_type, match_name,
                   team_a, team_b, team_a_score, team_b_score, 
                   match_ts_utc, match_date
            FROM Matches WHERE match_id = ?
        """, (match_id,))
        match = cur.fetchone()
        
        if not match:
            print(f"  ✗ Match not found!")
            issues.append(f"Match {match_id}: Not found")
            continue
        
        (mid, tournament, stage, match_type, match_name,
         team_a, team_b, team_a_score, team_b_score, 
         match_ts_utc, match_date) = match
        
        print(f"  Tournament: {tournament or 'N/A'}")
        print(f"  Stage: {stage or 'N/A'}")
        print(f"  Match Type: {match_type or 'N/A'}")
        print(f"  Match Name: {match_name or 'N/A'}")
        print(f"  Teams: {team_a or 'N/A'} vs {team_b or 'N/A'}")
        print(f"  Score: {team_a_score or 0} - {team_b_score or 0}")
        print(f"  Date: {match_date or 'N/A'}")
        print(f"  Timestamp: {match_ts_utc or 'N/A'}")
        
        # Check for issues
        match_issues = []
        if not team_a or team_a == 'Unknown':
            match_issues.append("Missing team_a")
        if not team_b or team_b == 'Unknown':
            match_issues.append("Missing team_b")
        if team_a_score is None or team_b_score is None:
            match_issues.append("Missing scores")
        if not match_type or match_type not in ['VCT', 'VCL', 'OFFSEASON', 'SHOWMATCH']:
            match_issues.append(f"Invalid match_type: {match_type}")
        if not match_ts_utc:
            match_issues.append("Missing timestamp")
        if not match_date:
            match_issues.append("Missing date")
        
        # Check maps
        cur.execute("SELECT COUNT(*) FROM Maps WHERE match_id = ?", (match_id,))
        map_count = cur.fetchone()[0]
        print(f"  Maps: {map_count}")
        
        if map_count == 0:
            match_issues.append("No maps found")
        else:
            cur.execute("""
                SELECT map, team_a_score, team_b_score 
                FROM Maps WHERE match_id = ? 
                ORDER BY game_id
            """, (match_id,))
            maps = cur.fetchall()
            print(f"  Map details:")
            for map_name, ta_score, tb_score in maps:
                print(f"    - {map_name}: {ta_score or 0} - {tb_score or 0}")
        
        # Check player stats
        cur.execute("SELECT COUNT(*) FROM Player_Stats WHERE match_id = ?", (match_id,))
        player_count = cur.fetchone()[0]
        print(f"  Player Stats: {player_count} entries")
        
        if player_count == 0:
            match_issues.append("No player stats found")
        else:
            # Sample a few players
            cur.execute("""
                SELECT player, team, agent, rating, acs, kills, deaths, assists
                FROM Player_Stats WHERE match_id = ?
                LIMIT 5
            """, (match_id,))
            players = cur.fetchall()
            print(f"  Sample players:")
            for player, team, agent, rating, acs, kills, deaths, assists in players:
                print(f"    - {player} ({team}): {agent}, Rating: {rating:.2f}, ACS: {acs}, K/D: {kills}/{deaths}")
        
        if match_issues:
            print(f"  [WARNING] Issues: {', '.join(match_issues)}")
            issues.append(f"Match {match_id}: {', '.join(match_issues)}")
        else:
            print(f"  [OK] All checks passed")
        
        print()
    
    conn.close()
    
    # Summary
    print(f"{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Total matches tested: {len(match_ids)}")
    print(f"Matches with issues: {len(issues)}")
    
    if issues:
        print("\nIssues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n[OK] All tested matches passed validation!")
    
    # Overall stats
    conn = get_conn()
    cur = conn.cursor()
    
    print(f"\n{'='*70}")
    print("DATABASE STATISTICS")
    print(f"{'='*70}")
    
    cur.execute("SELECT COUNT(*) FROM Matches")
    total = cur.fetchone()[0]
    print(f"Total matches: {total}")
    
    cur.execute("SELECT COUNT(*) FROM Matches WHERE match_type = 'VCT'")
    vct = cur.fetchone()[0]
    print(f"VCT matches: {vct}")
    
    cur.execute("SELECT COUNT(*) FROM Matches WHERE match_type = 'VCL'")
    vcl = cur.fetchone()[0]
    print(f"VCL matches: {vcl}")
    
    cur.execute("SELECT COUNT(*) FROM Matches WHERE match_type = 'SHOWMATCH'")
    showmatch = cur.fetchone()[0]
    print(f"SHOWMATCH matches: {showmatch}")
    
    cur.execute("SELECT COUNT(*) FROM Matches WHERE match_type = 'OFFSEASON'")
    offseason = cur.fetchone()[0]
    print(f"OFFSEASON matches: {offseason}")
    
    cur.execute("SELECT COUNT(*) FROM Matches WHERE match_type IS NULL OR match_type = ''")
    unclassified = cur.fetchone()[0]
    if unclassified > 0:
        print(f"Unclassified matches: {unclassified}")
    
    cur.execute("SELECT COUNT(*) FROM Maps")
    total_maps = cur.fetchone()[0]
    print(f"Total maps: {total_maps}")
    
    cur.execute("SELECT COUNT(*) FROM Player_Stats")
    total_stats = cur.fetchone()[0]
    print(f"Total player stat entries: {total_stats}")
    
    cur.execute("SELECT COUNT(DISTINCT team_a) + COUNT(DISTINCT team_b) FROM Matches")
    # Better way to count unique teams
    cur.execute("SELECT COUNT(DISTINCT team_a) FROM Matches WHERE team_a IS NOT NULL")
    teams_a = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT team_b) FROM Matches WHERE team_b IS NOT NULL")
    teams_b = cur.fetchone()[0]
    # Approximate unique teams (some may overlap)
    print(f"Approximate unique teams: {teams_a + teams_b}")
    
    conn.close()


if __name__ == '__main__':
    import sys
    num_samples = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    test_random_matches(num_samples)
