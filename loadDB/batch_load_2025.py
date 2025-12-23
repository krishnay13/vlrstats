"""
Batch load all VCT 2025 matches from matches_2025_full.txt into database.
Uses the improved scrape_2025_fresh.py scraper with proper error handling.
"""
import sys
import time
import sqlite3
from scrape_2025_fresh import scrape_player_data_from_table
from datetime import datetime


DB_PATH = "../valorant_esports.db"


def get_or_create_team(conn, team_name: str) -> int:
    """Get team ID or create new team."""
    cursor = conn.cursor()
    cursor.execute("SELECT team_id FROM Teams WHERE team_name = ?", (team_name,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    
    # Insert with NULL player IDs initially
    cursor.execute("INSERT INTO Teams (team_name) VALUES (?)", (team_name,))
    conn.commit()
    return cursor.lastrowid


def get_or_create_player(conn, player_name: str, team_name: str) -> int:
    """Get player ID or create new player."""
    cursor = conn.cursor()
    cursor.execute("SELECT player_id FROM Players WHERE player_name = ?", (player_name,))
    result = cursor.fetchone()
    
    if result:
        # Update team name if it changed
        cursor.execute("UPDATE Players SET team_name = ? WHERE player_id = ?", 
                      (team_name, result[0]))
        conn.commit()
        return result[0]
    
    cursor.execute("INSERT INTO Players (player_name, team_name) VALUES (?, ?)", 
                   (player_name, team_name))
    conn.commit()
    return cursor.lastrowid


def insert_match_data(conn, url: str, team1_name: str, team2_name: str, 
                     team1_score: int, team2_score: int, player_stats: list, 
                     map_names: list) -> bool:
    """Insert match and player stats into database."""
    try:
        cursor = conn.cursor()
        
        # Get or create teams
        team1_id = get_or_create_team(conn, team1_name)
        team2_id = get_or_create_team(conn, team2_name)
        
        # Insert match using the schema from db_init.py
        cursor.execute("""
            INSERT INTO Matches (team1_name, team2_name, team1_score, team2_score)
            VALUES (?, ?, ?, ?)
        """, (team1_name, team2_name, team1_score, team2_score))
        match_id = cursor.lastrowid
        
        # Insert maps using the schema from db_init.py
        for map_name in map_names:
            cursor.execute("""
                INSERT INTO Maps (match_id, map_name, team1_name, team2_name, 
                                 team1_score, team2_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (match_id, map_name, team1_name, team2_name, 0, 0))
        
        # Insert player stats using correct column names
        for stat in player_stats:
            player_id = get_or_create_player(conn, stat['player_name'], stat['team'])
            
            # Get the map_id for the first map (or NULL if no maps)
            cursor.execute("SELECT map_id FROM Maps WHERE match_id = ? LIMIT 1", (match_id,))
            map_result = cursor.fetchone()
            map_id = map_result[0] if map_result else None
            
            cursor.execute("""
                INSERT INTO Player_Stats 
                (player_id, match_id, map_id, agent, rating, acs, kills, deaths, assists, 
                 plus_minus, kast, adr, hs_percentage, fk, fd, f_plus_minus)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (player_id, match_id, map_id, stat.get('agent', 'Unknown'),
                  stat['rating'], stat['acs'], stat['kills'], stat['deaths'], 
                  stat['assists'], stat['plus_minus'], stat['kast'], 
                  stat['adr'], stat['hs_percentage'], stat['fk'], 
                  stat['fd'], stat['f_plus_minus']))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"    [ERROR] Database insert failed: {e}")
        conn.rollback()
        return False


def load_matches_from_file(filename: str = "matches_2025_full.txt", 
                           max_matches: int = None,
                           start_from: int = 0):
    """
    Load matches from file into database.
    
    Args:
        filename: File containing match URLs (one per line)
        max_matches: Maximum number of matches to load (None = all)
        start_from: Skip first N matches (for resuming)
    """
    # Read match URLs
    with open(filename, 'r') as f:
        match_urls = [line.strip() for line in f if line.strip()]
    
    total = len(match_urls)
    if start_from > 0:
        match_urls = match_urls[start_from:]
        print(f"Starting from match {start_from + 1}/{total}")
    
    if max_matches:
        match_urls = match_urls[:max_matches]
        print(f"Loading {len(match_urls)} matches (limited)")
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    
    # Stats tracking
    successful = 0
    failed = 0
    failed_urls = []
    
    print(f"\nLoading {len(match_urls)} matches into database...")
    print("=" * 70)
    
    for i, url in enumerate(match_urls, start_from + 1):
        print(f"[{i}/{total}] {url.split('/')[-1][:50]}...")
        
        try:
            # Scrape match data
            result = scrape_player_data_from_table(url)
            team1_name, team2_name, team1_score, team2_score, player_stats, map_names = result
            
            # Validate data
            if not team1_name or not team2_name:
                print(f"    [SKIP] Missing team names")
                failed += 1
                failed_urls.append(url)
                continue
            
            if len(player_stats) < 10:
                print(f"    [SKIP] Insufficient player data ({len(player_stats)} players)")
                failed += 1
                failed_urls.append(url)
                continue
            
            # Insert into database
            if insert_match_data(conn, url, team1_name, team2_name, 
                                team1_score, team2_score, player_stats, map_names):
                print(f"    [OK] {team1_name} {team1_score}-{team2_score} {team2_name}, {len(player_stats)} players")
                successful += 1
            else:
                failed += 1
                failed_urls.append(url)
            
        except Exception as e:
            print(f"    [ERROR] Scraping failed: {e}")
            failed += 1
            failed_urls.append(url)
        
        # Be polite to the server
        time.sleep(1.0)
    
    conn.close()
    
    # Summary
    print("\n" + "=" * 70)
    print(f"Loading complete!")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    
    if failed_urls:
        print(f"\nFailed URLs saved to 'failed_matches.txt'")
        with open('failed_matches.txt', 'w') as f:
            for url in failed_urls:
                f.write(f"{url}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Load VCT 2025 matches into database")
    parser.add_argument("--limit", type=int, help="Maximum number of matches to load")
    parser.add_argument("--start", type=int, default=0, help="Start from match N (for resuming)")
    parser.add_argument("--file", type=str, default="matches_2025_full.txt", 
                       help="File containing match URLs")
    
    args = parser.parse_args()
    
    print("VCT 2025 Batch Loader")
    print("=" * 70)
    
    try:
        load_matches_from_file(
            filename=args.file,
            max_matches=args.limit,
            start_from=args.start
        )
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] You can resume with --start <last_index>.")
