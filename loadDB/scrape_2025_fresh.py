"""
Improved VCT 2025 scraper with minimal guardrails.
Trusts VLR.gg structure and avoids hardcoded corrections.
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
    Minimal normalization: trim whitespace only.
    """
    if not team_name:
        return "Unknown"
    return ' '.join(team_name.split())


def scrape_player_data_from_table(url: str) -> Tuple[str, str, int, int, List[Dict], List[str]]:
    """
    Scrape match data trusting VLR.gg DOM.
    Returns: (team1_name, team2_name, team1_score, team2_score, player_stats, map_names)
    """
    try:
        response = SESSION.get(url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Team names from header
        team1_name = None
        team2_name = None
        header_teams = soup.select('.match-header-link-name .wf-title-med')
        if len(header_teams) >= 2:
            team1_name = header_teams[0].get_text(strip=True)
            team2_name = header_teams[1].get_text(strip=True)
        
        # Fallback to player table labels only if header missing
        if not team1_name or not team2_name:
            team_tags = soup.select('td.mod-player div.ge-text-light')
            teams_from_players = [tag.get_text(strip=True) for tag in team_tags]
            unique = []
            for t in teams_from_players:
                t = clean_team_name(t)
                if t and t not in unique:
                    unique.append(t)
            if len(unique) >= 2:
                team1_name, team2_name = unique[:2]
        
        team1_name = clean_team_name(team1_name)
        team2_name = clean_team_name(team2_name)
        
        # Scores
        team1_score = 0
        team2_score = 0
        score_elements = soup.select('.match-header-vs-score .js-spoiler span')
        if len(score_elements) >= 2:
            try:
                team1_score = int(score_elements[0].get_text(strip=True))
                team2_score = int(score_elements[1].get_text(strip=True))
            except ValueError:
                pass
        
        # Player stats from All Maps
        all_stats_div = soup.find('div', {'data-game-id': 'all'}) or soup.find('div', class_='vm-stats-game')
        player_rows = (all_stats_div.select('table.wf-table-inset tbody tr') if all_stats_div
                       else soup.select('table.wf-table-inset tbody tr'))
        
        player_stats = []
        for row in player_rows[:10]:
            cells = row.find_all('td')
            if len(cells) < 7:
                continue
            player_cell = cells[0]
            player_name_elem = player_cell.find('div', class_='text-of')
            team_elem = player_cell.find('div', class_='ge-text-light')
            player_name = player_name_elem.get_text(strip=True) if player_name_elem else "Unknown"
            team = clean_team_name(team_elem.get_text(strip=True) if team_elem else "Unknown")
            agent_elem = player_cell.find('img', class_='mod-sm')
            agent = agent_elem.get('title', 'Unknown') if agent_elem else 'Unknown'
            
            def first_num(text, default=0.0, as_int=False):
                text = (text or '').strip().replace('\n', ' ')
                parts = text.split()
                for part in parts:
                    cleaned = ''.join(c for c in part if c.isdigit() or c in '.-')
                    if cleaned and cleaned not in '.-':
                        try:
                            val = float(cleaned)
                            return int(val) if as_int else val
                        except:
                            pass
                return default
            
            rating = first_num(cells[2].get_text() if len(cells) > 2 else '')
            acs = first_num(cells[3].get_text() if len(cells) > 3 else '', as_int=True)
            kills = first_num(cells[4].get_text() if len(cells) > 4 else '', as_int=True)
            deaths = first_num(cells[5].get_text() if len(cells) > 5 else '', as_int=True)
            assists = first_num(cells[6].get_text() if len(cells) > 6 else '', as_int=True)
            
            player_stats.append({
                'player_name': player_name,
                'team': team,
                'agent': agent,
                'rating': rating,
                'acs': acs,
                'kills': kills,
                'deaths': deaths,
                'assists': assists,
                # leave derived stats empty to be computed downstream
            })
        
        # Map names
        map_names = []
        for map_elem in soup.select('.vm-stats-gamesnav-item'):
            game_id = map_elem.get('data-game-id', '')
            if game_id and game_id != 'all':
                map_names.append(map_elem.get_text(strip=True))
        
        return team1_name or 'Unknown', team2_name or 'Unknown', team1_score, team2_score, player_stats, map_names
        
    except Exception as e:
        print(f"  [ERROR] Error scraping {url}: {e}")
        return "Unknown", "Unknown", 0, 0, [], []


def scrape_vct_2025_events() -> List[Tuple[str, str]]:
    """
    Scrape VCT 2025 event list.
    """
    events = []
    try:
        response = requests.get('https://www.vlr.gg/vct-2025', timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Trust site: collect /event/<id> links
        for link in soup.find_all('a', href=re.compile(r'/event/\d+')):
            href = link.get('href', '')
            name = link.get_text(strip=True)
            if href.startswith('/event/') and name:
                url = f"https://www.vlr.gg{href}"
                if (name, url) not in events:
                    events.append((name, url))
        print(f"[OK] Found {len(events)} VCT 2025 events")
        return events
    except Exception as e:
        print(f"[ERROR] Error scraping events: {e}")
        return []


def scrape_event_matches(event_url: str, limit: Optional[int] = None) -> List[str]:
    """
    Scrape match URLs from an event page.
    """
    matches = []
    try:
        matches_url = event_url.rstrip('/') + '/matches'
        response = requests.get(matches_url, timeout=10)
        if response.status_code != 200:
            response = requests.get(event_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Accept links with numeric id segment
        for link in soup.find_all('a', href=re.compile(r'/\d+/')):
            href = link.get('href', '')
            parts = href.split('/')
            if len(parts) >= 3 and parts[1].isdigit():
                url = f"https://www.vlr.gg{href}"
                if url not in matches:
                    matches.append(url)
                    if limit and len(matches) >= limit:
                        break
        print(f"  Found {len(matches)} matches in event")
        return matches
    except Exception as e:
        print(f"  [ERROR] Error scraping event matches: {e}")
        return []


def main():
    print("=" * 70)
    print("VCT 2025 SCRAPER - MINIMAL GUARDRAILS")
    print("=" * 70)
    
    print("\n[1] Scraping VCT 2025 events...")
    events = scrape_vct_2025_events()
    if not events:
        print("[ERROR] No events found. Check VLR.gg website structure.")
        return
    
    print(f"\nFound {len(events)} events:")
    for idx, (name, url) in enumerate(events[:10], 1):
        print(f"  {idx}. {name}")
    
    print(f"\n[2] Scraping matches from first event: {events[0][0]}...")
    match_urls = scrape_event_matches(events[0][1])
    if not match_urls:
        print("[ERROR] No matches found.")
        return
    
    print(f"\n[3] Testing scrape on first match...")
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
    
    output_file = 'loadDB/matches_2025.txt'
    with open(output_file, 'w') as f:
        for url in match_urls:
            f.write(url + '\n')
    print(f"\n[OK] Saved {len(match_urls)} match URLs to {output_file}")
    print("\nNext: Process these matches with LoadStats.py")


if __name__ == '__main__':
    main()
