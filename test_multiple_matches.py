"""Test extraction on multiple matches to see if they have map/player data"""
import asyncio
from loadDB.vlr_ingest import scrape_match

async def test_multiple():
    # Test a few different matches
    test_matches = [378662, 378663, 378657, 378656, 378667]
    
    print("Testing map/player extraction on multiple matches...")
    print("=" * 70)
    
    for match_id in test_matches:
        try:
            match_row, maps_info, players_info = await scrape_match(match_id)
            print(f"\nMatch {match_id}: {match_row[5]} vs {match_row[6]} ({match_row[7]}-{match_row[8]})")
            print(f"  Maps: {len(maps_info)}")
            print(f"  Players: {len(players_info)}")
            if maps_info:
                print(f"  Map details: {[(m[2], f'{m[3]}-{m[4]}') for m in maps_info[:2]]}")
        except Exception as e:
            print(f"\nMatch {match_id}: ERROR - {e}")

if __name__ == '__main__':
    asyncio.run(test_multiple())
