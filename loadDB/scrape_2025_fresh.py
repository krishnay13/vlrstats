"""
Improved VCT 2025 scraper with proper team name handling.
Fixes issues like "Gen.G Edward Gaming" being incorrectly merged.
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import re
import time
import json
from typing import List, Dict, Tuple, Optional


# Robust HTTP session with retries
def _build_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

SESSION = _build_session()


def clean_team_name(team_name: str) -> str:
    """
    Clean and normalize team names.
    Handles cases like:
    - "Gen.G EDward Gaming" -> should stay as is or be split
    - Extra whitespace, special chars, etc.
    """
    # Remove excessive whitespace
    team_name = ' '.join(team_name.split())
    
    # Common team name corrections
    corrections = {
        "Gen.G EDward Gaming": "Gen.G",  # This was actually Gen.G playing
        "EDward Gaming Gen.G": "EDward Gaming",
        "Gen.G Edward Gaming": "Gen.G",
    }
    
    return corrections.get(team_name, team_name)


def scrape_player_data_from_table(url: str) -> Tuple[str, str, int, int, List[Dict], List[str]]:
    """
    Scrape match data with improved team name parsing.
    Returns: (team1_name, team2_name, team1_score, team2_score, player_stats, map_names)
    """
    try:
        response = SESSION.get(url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract team names from header (more reliable)
        team1_name = None
        team2_name = None
        
        # Method 1: From match header
        header_teams = soup.select('.match-header-link-name .wf-title-med')
        if len(header_teams) >= 2:
            team1_name = header_teams[0].get_text(strip=True)
            team2_name = header_teams[1].get_text(strip=True)
        
        # Method 2: From player table team tags (fallback)
        if not team1_name or not team2_name:
            team_tags = soup.select('td.mod-player div.ge-text-light')
            if len(team_tags) >= 10:
                teams_from_players = list(set([tag.get_text(strip=True) for tag in team_tags[:10]]))
                if len(teams_from_players) == 2:
                    team1_name = teams_from_players[0]
                    team2_name = teams_from_players[1]
        
        # Clean team names
        team1_name = clean_team_name(team1_name) if team1_name else "Unknown Team 1"
        team2_name = clean_team_name(team2_name) if team2_name else "Unknown Team 2"
        
        # Extract scores
        team1_score = 0
        team2_score = 0
        score_elements = soup.select('.match-header-vs-score .js-spoiler span')
        if len(score_elements) >= 2:
            try:
                team1_score = int(score_elements[0].get_text(strip=True))
                team2_score = int(score_elements[1].get_text(strip=True))
            except ValueError:
                pass
        
        # Extract player stats from "All Maps" overview table
        # Find the stats container for data-game-id="all"
        all_stats_div = soup.find('div', {'data-game-id': 'all'})
        if not all_stats_div:
            # Fallback: find first stats game div
            all_stats_div = soup.find('div', class_='vm-stats-game')
        
        player_stats = []
        if all_stats_div:
            player_rows = all_stats_div.select('table.wf-table-inset tbody tr')
        else:
            # Last resort fallback
            player_rows = soup.select('table.wf-table-inset tbody tr')
        
        for row in player_rows[:10]:  # First 10 players only (5v5)
            try:
                cells = row.find_all('td')
                if len(cells) < 14:
                    continue
                
                # Player name and team
                player_cell = cells[0]
                player_name_elem = player_cell.find('div', class_='text-of')
                team_elem = player_cell.find('div', class_='ge-text-light')
                
                player_name = player_name_elem.get_text(strip=True) if player_name_elem else "Unknown"
                team = team_elem.get_text(strip=True) if team_elem else "Unknown"
                team = clean_team_name(team)
                
                # Agent
                agent_elem = player_cell.find('img', class_='mod-sm')
                agent = agent_elem.get('title', 'Unknown') if agent_elem else 'Unknown'
                
                # Stats - handle multiple numbers in cell text
                def extract_first_number(text, default=0.0, as_int=False):
                    """Extract first number from text like '1.501.881.11' -> 1.50"""
                    try:
                        # Clean text and try to parse first reasonable number
                        text = text.strip().replace('\n', ' ')
                        # Split on whitespace and try each token
                        parts = text.split()
                        for part in parts:
                            # Remove any non-numeric chars except . and -
                            cleaned = ''.join(c for c in part if c.isdigit() or c in '.-')
                            if cleaned and cleaned not in '.-':
                                try:
                                    val = float(cleaned)
                                    return int(val) if as_int else val
                                except:
                                    continue
                        return default
                    except:
                        return default
                
                # Extract stats - look for spans with class 'side' or 'mod-both' (overview totals)
                rating_span = cells[2].find('span', class_='side') if len(cells) > 2 else None
                acs_span = cells[3].find('span', class_='side') if len(cells) > 3 else None  
                kills_span = cells[4].find('span', class_='side') if len(cells) > 4 else None
                deaths_span = cells[5].find('span', class_='side') if len(cells) > 5 else None
                assists_span = cells[6].find('span', class_='side') if len(cells) > 6 else None
                
                rating = extract_first_number(rating_span.get_text() if rating_span else cells[2].get_text())
                acs = extract_first_number(acs_span.get_text() if acs_span else cells[3].get_text(), as_int=True)
                kills = extract_first_number(kills_span.get_text() if kills_span else cells[4].get_text(), as_int=True)
                deaths = extract_first_number(deaths_span.get_text() if deaths_span else cells[5].get_text(), as_int=True)
                assists = extract_first_number(assists_span.get_text() if assists_span else cells[6].get_text(), as_int=True)
                
                player_stats.append({
                    'player_name': player_name,
                    'team': team,
                    'agent': agent,
                    'rating': rating,
                    'acs': acs,
                    'kills': kills,
                    'deaths': deaths,
                    'assists': assists,
                    'plus_minus': '+0',  # Placeholder
                    'kast': '0%',
                    'adr': 0,
                    'hs_percentage': '0%',
                    'fk': 0,
                    'fd': 0,
                    'f_plus_minus': '+0'
                })
            except Exception as e:
                print(f"    Error parsing player row: {e}")
                continue
        
        # Extract map names
        map_names = []
        map_elements = soup.select('.vm-stats-gamesnav-item')
        for map_elem in map_elements:
            map_name = map_elem.get_text(strip=True)
            game_id = map_elem.get('data-game-id', '')
            if game_id and game_id != 'all':
                map_names.append(map_name)
        
        return team1_name, team2_name, team1_score, team2_score, player_stats, map_names
        
    except Exception as e:
        print(f"  [ERROR] Error scraping {url}: {e}")
        return "Unknown", "Unknown", 0, 0, [], []


def scrape_vct_2025_events() -> List[Tuple[str, str]]:
    """
    Scrape VCT 2025 event list.
    Returns: [(event_name, event_url), ...]
    """
    events = []
    try:
        response = requests.get('https://www.vlr.gg/vct-2025', timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find event links
        event_links = soup.find_all('a', href=re.compile(r'/event/\d+'))
        
        for link in event_links:
            href = link.get('href', '')
            if href.startswith('/event/'):
                event_name = link.get_text(strip=True)
                event_url = f"https://www.vlr.gg{href}"
                
                # Avoid duplicates
                if (event_name, event_url) not in events and event_name:
                    events.append((event_name, event_url))
        
        print(f"[OK] Found {len(events)} VCT 2025 events")
        return events
    except Exception as e:
        print(f"[ERROR] Error scraping events: {e}")
        return []


def scrape_event_matches(event_url: str, limit: int = 50) -> List[str]:
    """
    Scrape match URLs from an event page.
    """
    matches = []
    try:
        # Try the matches subpage first
        matches_url = event_url.rstrip('/') + '/matches'
        response = requests.get(matches_url, timeout=10)
        
        if response.status_code != 200:
            # Fallback to main event page
            response = requests.get(event_url, timeout=10)
        
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find match links
        match_links = soup.find_all('a', href=re.compile(r'/\d+/'))
        
        for link in match_links:
            href = link.get('href', '')
            # Match URLs typically look like: /{match_id}/{team1}-vs-{team2}
            if re.match(r'/\d+/[^/]+', href):
                match_url = f"https://www.vlr.gg{href}"
                if match_url not in matches:
                    matches.append(match_url)
                    if len(matches) >= limit:
                        break
        
        print(f"  Found {len(matches)} matches in event")
        return matches
    except Exception as e:
        print(f"  [ERROR] Error scraping event matches: {e}")
        return []


def main():
    """Main scraping routine for 2025 VCT data."""
    print("=" * 70)
    print("VCT 2025 SCRAPER - IMPROVED VERSION")
    print("=" * 70)
    
    # Scrape events
    print("\n[1] Scraping VCT 2025 events...")
    events = scrape_vct_2025_events()
    
    if not events:
        print("[ERROR] No events found. Check VLR.gg website structure.")
        return
    
    print(f"\nFound {len(events)} events:")
    for idx, (name, url) in enumerate(events[:10], 1):
        print(f"  {idx}. {name}")
    
    # Scrape matches from first event
    print(f"\n[2] Scraping matches from first event: {events[0][0]}...")
    match_urls = scrape_event_matches(events[0][1], limit=10)
    
    if not match_urls:
        print("[ERROR] No matches found.")
        return
    
    # Test scraping first match
    print(f"\n[3] Testing scrape on first match...")
    if match_urls:
        test_url = match_urls[0]
        print(f"  URL: {test_url}")
        
        team1, team2, score1, score2, players, maps = scrape_player_data_from_table(test_url)
        
        print(f"\n  Match: {team1} vs {team2}")
        print(f"  Score: {score1} - {score2}")
        print(f"  Players scraped: {len(players)}")
        print(f"  Maps: {', '.join(maps) if maps else 'None'}")
        
        if players:
            print(f"\n  Sample players:")
            for p in players[:3]:
                print(f"    {p['player_name']} ({p['team']}) - {p['kills']}K / {p['deaths']}D")
    
    # Save match URLs for batch processing
    output_file = 'loadDB/matches_2025.txt'
    with open(output_file, 'w') as f:
        for url in match_urls:
            f.write(url + '\n')
    
    print(f"\n[OK] Saved {len(match_urls)} match URLs to {output_file}")
    print("\nNext: Process these matches with LoadStats.py")


if __name__ == '__main__':
    main()
