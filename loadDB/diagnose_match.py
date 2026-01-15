"""Diagnostic script to inspect a problematic match and see what's happening."""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from .vlr_ingest import fetch_html, scrape_match

async def diagnose(match_id: int):
    """Diagnose a specific match to see why it's showing as a draw."""
    print(f"\n=== Diagnosing Match {match_id} ===\n")
    
    match_row, maps_info, players_info, _ = await scrape_match(match_id)
    
    print(f"Match ID: {match_row[0]}")
    print(f"Teams: {match_row[5]} vs {match_row[6]}")
    print(f"Match Score: {match_row[7]}-{match_row[8]}")
    print(f"Tournament: {match_row[1]}")
    print(f"Match Name: {match_row[4]}")
    print(f"\nMaps ({len(maps_info)}):")
    for mid, gid, map_name, ta, tb in maps_info:
        print(f"  Map {gid} ({map_name}): {ta}-{tb}")
    
    # Fetch raw HTML to inspect
    url = f"https://www.vlr.gg/{match_id}"
    async with aiohttp.ClientSession() as session:
        html = await fetch_html(session, url)
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Check for score in header
    score_elem = soup.select_one('.match-header-vs-score')
    if score_elem:
        print(f"\nHeader Score Element: {score_elem.get_text(strip=True)}")
        print(f"Header Score HTML: {str(score_elem)[:200]}")
    
    # Check all game divs
    game_divs = soup.select('div.vm-stats-game[data-game-id]')
    print(f"\nFound {len(game_divs)} game divs:")
    for div in game_divs:
        gid = div.get('data-game-id')
        header = div.find('div', class_='vm-stats-game-header')
        if header:
            header_text = header.get_text(' ', strip=True)
            print(f"  Game {gid}: {header_text[:100]}")
    
    # Check for live/upcoming indicators
    status = soup.select('.match-header-status, .match-status')
    if status:
        print(f"\nStatus indicators: {[s.get_text(strip=True) for s in status]}")
    
    # Check page title
    title = soup.find('title')
    if title:
        print(f"\nPage Title: {title.get_text()}")

if __name__ == '__main__':
    import sys
    match_id = int(sys.argv[1]) if len(sys.argv) > 1 else 295607
    asyncio.run(diagnose(match_id))
