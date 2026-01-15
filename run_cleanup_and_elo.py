#!/usr/bin/env python3
"""
Script to delete showmatches and compute Elo ratings.

This script:
1. Deletes all showmatches from the database (comprehensive detection)
2. Computes and saves Elo ratings to the database
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loadDB.cli import main as cli_main
from loadDB.elo import compute_elo
import argparse

def main():
    print("=" * 70)
    print("Showmatch Cleanup and Elo Computation")
    print("=" * 70)
    
    # Step 1: Delete showmatches
    print("\n[1/2] Deleting showmatches from database...")
    print("-" * 70)
    
    # Create a mock args object for remove-showmatches
    class Args:
        def __init__(self):
            self.cmd = "remove-showmatches"
            self.dry_run = False
    
    args = Args()
    
    # Import and run the remove-showmatches logic
    from loadDB.db_utils import get_conn
    from loadDB.normalizers.team import normalize_team
    import sqlite3
    
    def is_showmatch_team(team_name: str) -> bool:
        """Check if a team name is a showmatch team."""
        if not team_name:
            return False
        
        name = team_name.lower().strip()
        
        showmatch_teams = [
            'team international', 'team spain', 'team china', 'team tarik',
            'team thailand', 'team world', 'glory once again', 'team emea',
            'team france', 'team toast', 'team alpha', 'team omega',
            'pure aim', 'precise defeat',
            'alp', 'cjmz', 'cn', 'emea', 'eq118', 'fra', 'goa', 'hs',
            'intl', 'ome', 'team', 'wor', 'thai',
            'dank1ng', 'dohyeon', 'fugu', 'heart bus', 'jisou', 'karsaj',
            'sergioferra', 'spicyuuu', 'tarik', 'xiaojue', 'yjj', 'zhang yanqi',
        ]
        
        if name in showmatch_teams:
            return True
        
        if 'team ' in name and any(indicator in name for indicator in [
            'showmatch', 'all-star', 'international', 'spain', 'china',
            'tarik', 'thailand', 'world', 'emea', 'france', 'toast',
            'alpha', 'omega'
        ]):
            return True
        
        if 'glory once again' in name:
            return True
        
        return False
    
    conn = get_conn()
    cur = conn.cursor()
    
    # Comprehensive showmatch detection
    cur.execute("SELECT match_id FROM Matches WHERE match_type = 'SHOWMATCH'")
    match_ids_by_type = {row[0] for row in cur.fetchall()}
    
    cur.execute("SELECT match_id, team_a, team_b FROM Matches")
    all_matches = cur.fetchall()
    match_ids_by_teams = set()
    
    for match_id, team_a, team_b in all_matches:
        team_a_norm = normalize_team(team_a) if team_a else ""
        team_b_norm = normalize_team(team_b) if team_b else ""
        
        if is_showmatch_team(team_a_norm) or is_showmatch_team(team_b_norm):
            match_ids_by_teams.add(match_id)
    
    cur.execute("SELECT match_id, tournament, stage, match_name FROM Matches")
    match_ids_by_name = set()
    
    for match_id, tournament, stage, match_name in cur.fetchall():
        tournament_lower = (tournament or '').lower()
        stage_lower = (stage or '').lower()
        match_name_lower = (match_name or '').lower()
        
        if any('showmatch' in text or 'all-star' in text for text in [tournament_lower, stage_lower, match_name_lower]):
            match_ids_by_name.add(match_id)
    
    all_match_ids = match_ids_by_type | match_ids_by_teams | match_ids_by_name
    
    if all_match_ids:
        print(f"Found {len(all_match_ids)} showmatch match(es) to delete:")
        print(f"  - {len(match_ids_by_type)} by match_type = 'SHOWMATCH'")
        print(f"  - {len(match_ids_by_teams)} by showmatch teams")
        print(f"  - {len(match_ids_by_name)} by tournament/stage/match_name containing 'showmatch'")
        
        match_ids_list = list(all_match_ids)
        placeholders = ','.join('?' * len(match_ids_list))
        
        cur.execute(f"DELETE FROM Player_Stats WHERE match_id IN ({placeholders})", match_ids_list)
        player_stats_deleted = cur.rowcount
        
        cur.execute(f"DELETE FROM Maps WHERE match_id IN ({placeholders})", match_ids_list)
        maps_deleted = cur.rowcount
        
        cur.execute(f"DELETE FROM Matches WHERE match_id IN ({placeholders})", match_ids_list)
        matches_deleted = cur.rowcount
        
        conn.commit()
        
        print(f"\nDeleted:")
        print(f"  {matches_deleted} match(es)")
        print(f"  {maps_deleted} map(s)")
        print(f"  {player_stats_deleted} player stat record(s)")
    else:
        print("No showmatches found in database.")
    
    conn.close()
    
    # Step 2: Compute Elo
    print("\n[2/2] Computing Elo ratings...")
    print("-" * 70)
    compute_elo(save=True, top=20)
    
    print("\n" + "=" * 70)
    print("Cleanup and Elo computation complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()
