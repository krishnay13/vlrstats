"""Test score extraction for a specific match."""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from .vlr_ingest import fetch_html

async def test_extraction(match_id: int):
    """Test score extraction for match 508817."""
    url = f"https://www.vlr.gg/{match_id}"
    async with aiohttp.ClientSession() as session:
        html = await fetch_html(session, url)
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find the first game div
    game_divs = soup.select('div.vm-stats-game[data-game-id]')
    if not game_divs:
        print("No game divs found")
        return
    
    game_div = game_divs[0]
    game_id = game_div.get('data-game-id')
    print(f"Testing game {game_id}\n")
    
    # Find header
    header = game_div.find('div', class_='vm-stats-game-header')
    if not header:
        print("No header found")
        return
    
    print("=== Header HTML ===")
    print(str(header)[:1000])
    print("\n")
    
    # Try to find score elements
    print("=== Looking for score elements ===")
    score_elems = header.select('div.score, div[class*="score"]')
    print(f"Found {len(score_elems)} score elements with selector")
    for i, elem in enumerate(score_elems):
        print(f"  {i+1}. {elem.get('class')} -> '{elem.get_text(strip=True)}'")
    
    # Also try finding all divs
    all_divs = header.find_all('div')
    print(f"\nTotal divs in header: {len(all_divs)}")
    for div in all_divs:
        classes = div.get('class', [])
        if classes and any('score' in str(c).lower() for c in classes):
            print(f"  Found score div: classes={classes}, text='{div.get_text(strip=True)}'")
    
    # Try finding team containers
    print("\n=== Looking for team containers ===")
    team_containers = header.select('div.team, div[class*="team"]')
    print(f"Found {len(team_containers)} team containers")
    for i, team in enumerate(team_containers):
        print(f"  Team {i+1}: classes={team.get('class')}")
        score_in_team = team.select('.score, [class*="score"]')
        print(f"    Scores in team: {len(score_in_team)}")
        for score_elem in score_in_team:
            print(f"      Score: classes={score_elem.get('class')}, text='{score_elem.get_text(strip=True)}'")

if __name__ == '__main__':
    asyncio.run(test_extraction(508817))
