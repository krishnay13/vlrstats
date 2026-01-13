"""Re-scrape matches to update scores, maps, and player stats"""
import asyncio
import sqlite3
from loadDB.db_utils import get_conn, upsert_match, upsert_maps, upsert_player_stats
from loadDB.vlr_ingest import scrape_match

async def update_match_scores():
    """Re-scrape matches that have 0-0 scores to get actual scores"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Find matches with 0-0 scores
    cur.execute("""
        SELECT match_id FROM Matches 
        WHERE (team_a_score = 0 AND team_b_score = 0)
        ORDER BY match_date DESC
    """)
    match_ids = [row[0] for row in cur.fetchall()]
    
    print(f"Found {len(match_ids)} matches with 0-0 scores")
    print("Re-scraping to update scores, maps, and player stats...")
    print("=" * 70)
    
    updated = 0
    errors = 0
    
    for i, match_id in enumerate(match_ids, 1):
        try:
            print(f"[{i}/{len(match_ids)}] Scraping match {match_id}...", end=' ')
            match_row, maps_info, players_info = await scrape_match(match_id)
            
            # Update match_type from existing record
            cur.execute("SELECT match_type FROM Matches WHERE match_id = ?", (match_id,))
            existing_type = cur.fetchone()
            if existing_type and existing_type[0]:
                match_row_list = list(match_row)
                match_row_list[3] = existing_type[0]  # Preserve existing match_type
                match_row = tuple(match_row_list)
            
            # Upsert match data
            upsert_match(conn, match_row)
            
            # Upsert maps and get lookup
            map_lookup = {}
            if maps_info:
                map_lookup = upsert_maps(conn, maps_info)
            
            # Upsert player stats (requires map_lookup)
            if players_info:
                upsert_player_stats(conn, players_info, map_lookup)
            
            conn.commit()
            
            a_score = match_row[7]
            b_score = match_row[8]
            print(f"Score: {a_score}-{b_score}, Maps: {len(maps_info)}, Players: {len(players_info)}")
            updated += 1
            
        except Exception as e:
            print(f"ERROR: {e}")
            errors += 1
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print(f"Update complete: {updated} matches updated, {errors} errors")
    
    # Check final stats
    cur.execute("SELECT COUNT(*) FROM Matches WHERE team_a_score > 0 OR team_b_score > 0")
    with_scores = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Maps")
    total_maps = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Player_Stats")
    total_players = cur.fetchone()[0]
    
    print(f"\nDatabase stats:")
    print(f"  Matches with scores: {with_scores}")
    print(f"  Total maps: {total_maps}")
    print(f"  Total player stat entries: {total_players}")
    
    conn.close()

if __name__ == '__main__':
    asyncio.run(update_match_scores())
