"""Extract maps and player stats for all matches"""
import asyncio
import sqlite3
from loadDB.db_utils import get_conn, upsert_match, upsert_maps, upsert_player_stats
from loadDB.vlr_ingest import scrape_match

async def extract_all_data():
    """Re-scrape all matches to extract maps and player stats"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Get all match IDs
    cur.execute("SELECT match_id FROM Matches ORDER BY match_date DESC")
    match_ids = [row[0] for row in cur.fetchall()]
    
    print(f"Found {len(match_ids)} matches")
    print("Extracting maps and player stats for all matches...")
    print("=" * 70)
    
    updated = 0
    errors = 0
    total_maps = 0
    total_players = 0
    
    for i, match_id in enumerate(match_ids, 1):
        try:
            # Check if we already have maps for this match
            cur.execute("SELECT COUNT(*) FROM Maps WHERE match_id = ?", (match_id,))
            existing_maps = cur.fetchone()[0]
            
            if existing_maps > 0:
                # Skip if we already have maps
                if i % 100 == 0:
                    print(f"[{i}/{len(match_ids)}] Skipping match {match_id} (already has {existing_maps} maps)")
                continue
            
            if i % 10 == 0 or i <= 5:
                print(f"[{i}/{len(match_ids)}] Scraping match {match_id}...", end=' ')
            
            match_row, maps_info, players_info = await scrape_match(match_id)
            
            # Preserve existing match_type
            cur.execute("SELECT match_type FROM Matches WHERE match_id = ?", (match_id,))
            existing_type = cur.fetchone()
            if existing_type and existing_type[0]:
                match_row_list = list(match_row)
                match_row_list[3] = existing_type[0]
                match_row = tuple(match_row_list)
            
            # Upsert match (to update any changed data)
            upsert_match(conn, match_row)
            
            # Upsert maps and get lookup
            map_lookup = {}
            if maps_info:
                map_lookup = upsert_maps(conn, maps_info)
                total_maps += len(maps_info)
            
            # Upsert player stats
            if players_info:
                upsert_player_stats(conn, players_info, map_lookup)
                total_players += len(players_info)
            
            conn.commit()
            
            if i % 10 == 0 or i <= 5:
                print(f"Maps: {len(maps_info)}, Players: {len(players_info)}")
            
            updated += 1
            
        except Exception as e:
            if i <= 10:
                print(f"ERROR: {e}")
                import traceback
                traceback.print_exc()
            errors += 1
    
    print("\n" + "=" * 70)
    print(f"Extraction complete!")
    print(f"  Matches processed: {updated}")
    print(f"  Errors: {errors}")
    print(f"  Total maps extracted: {total_maps}")
    print(f"  Total player stats extracted: {total_players}")
    
    # Final stats
    cur.execute("SELECT COUNT(*) FROM Maps")
    total_maps_db = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Player_Stats")
    total_players_db = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Matches WHERE (SELECT COUNT(*) FROM Maps WHERE Maps.match_id = Matches.match_id) > 0")
    matches_with_maps = cur.fetchone()[0]
    
    print(f"\nDatabase stats:")
    print(f"  Total maps in DB: {total_maps_db}")
    print(f"  Total player stats in DB: {total_players_db}")
    print(f"  Matches with maps: {matches_with_maps}")
    
    conn.close()

if __name__ == '__main__':
    asyncio.run(extract_all_data())
