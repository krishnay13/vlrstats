"""Test if maps and player stats are being upserted correctly"""
import asyncio
import sqlite3
from loadDB.db_utils import get_conn, upsert_match, upsert_maps, upsert_player_stats
from loadDB.vlr_ingest import scrape_match

async def test_upsert():
    # Test with a match we know has data
    match_id = 378662
    
    print(f"Testing upsert for match {match_id}...")
    print("=" * 70)
    
    # Scrape the match
    match_row, maps_info, players_info = await scrape_match(match_id)
    
    print(f"Scraped data:")
    print(f"  Maps: {len(maps_info)}")
    print(f"  Player stats: {len(players_info)}")
    
    if maps_info:
        print(f"\nSample maps:")
        for mid, game_id, map_name, ta_score, tb_score in maps_info[:3]:
            print(f"  - {map_name}: {ta_score}-{tb_score} (game_id: {game_id})")
    
    if players_info:
        print(f"\nSample players:")
        for mid, game_id, player, team, agent, rating, acs, kills, deaths, assists in players_info[:3]:
            print(f"  - {player} ({team}): {kills}/{deaths}/{assists}")
    
    # Now try to upsert
    conn = get_conn()
    
    print(f"\nUpserting data...")
    try:
        # Upsert match
        upsert_match(conn, match_row)
        print("  [OK] Match upserted")
        
        # Upsert maps
        if maps_info:
            print(f"  Upserting {len(maps_info)} maps...")
            map_lookup = upsert_maps(conn, maps_info)
            print(f"  [OK] Maps upserted: {len(map_lookup)} maps")
        else:
            print("  [WARNING] No maps to upsert")
        
        # Upsert player stats (requires map_lookup)
        if players_info:
            print(f"  Upserting {len(players_info)} player stats...")
            upsert_player_stats(conn, players_info, map_lookup)
            print(f"  [OK] Player stats upserted")
        else:
            print("  [WARNING] No player stats to upsert")
        
        conn.commit()
        
        # Verify they were saved
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM Maps WHERE match_id = ?", (match_id,))
        maps_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM Player_Stats WHERE match_id = ?", (match_id,))
        players_count = cur.fetchone()[0]
        
        print(f"\nVerification:")
        print(f"  Maps in DB for this match: {maps_count}")
        print(f"  Player stats in DB for this match: {players_count}")
        
        if maps_count == 0 and len(maps_info) > 0:
            print("\n[ERROR] Maps were extracted but not saved!")
        if players_count == 0 and len(players_info) > 0:
            print("\n[ERROR] Player stats were extracted but not saved!")
            
    except Exception as e:
        print(f"\n[ERROR] Exception during upsert: {e}")
        import traceback
        traceback.print_exc()
    
    conn.close()

if __name__ == '__main__':
    asyncio.run(test_upsert())
