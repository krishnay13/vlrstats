"""Debug score extraction for a specific match."""
import asyncio
from .vlr_ingest import scrape_match

async def debug(match_id: int):
    """Debug score extraction."""
    print(f"\n=== Debugging Match {match_id} ===\n")
    
    match_row, maps_info, players_info, _ = await scrape_match(match_id)
    
    print(f"Maps ({len(maps_info)}):")
    for mid, gid, map_name, ta, tb in maps_info:
        print(f"  Map {gid} ({map_name}): {ta}-{tb}")

if __name__ == '__main__':
    import sys
    match_id = int(sys.argv[1]) if len(sys.argv) > 1 else 508817
    asyncio.run(debug(match_id))
