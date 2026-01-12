"""
Scrape all VCT tournaments from vct-2024 and vct-2025 pages and extract all match IDs.
"""
import re
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple
from .tournament_scraper import fetch_html, extract_event_id_from_url


async def scrape_vct_tournaments(vct_url: str) -> List[Dict[str, str]]:
    """
    Scrape all tournament event URLs from a VCT year page (e.g., vct-2024, vct-2025).
    
    Returns list of dicts with 'name', 'url', 'event_id'
    """
    async with aiohttp.ClientSession() as session:
        html = await fetch_html(session, vct_url)
    
    soup = BeautifulSoup(html, 'html.parser')
    tournaments = []
    
    # Find all tournament links - they're typically in event cards
    # Look for links that contain /event/ followed by a number
    event_links = soup.find_all('a', href=re.compile(r'/event/\d+'))
    
    seen_event_ids = set()
    for link in event_links:
        href = link.get('href', '')
        if not href:
            continue
        
        # Extract event ID
        event_id = extract_event_id_from_url(href)
        if not event_id or event_id in seen_event_ids:
            continue
        
        seen_event_ids.add(event_id)
        
        # Get tournament name from link text or nearby elements
        name = link.get_text(strip=True)
        if not name or len(name) < 3:
            # Try to get name from parent or nearby elements
            parent = link.parent
            for _ in range(5):
                if parent:
                    # Look for text in parent that might be the tournament name
                    parent_text = parent.get_text(' ', strip=True)
                    # Try to find a meaningful name (not just numbers/symbols)
                    if parent_text and len(parent_text) > len(name) and any(c.isalpha() for c in parent_text):
                        # Take first line or first meaningful chunk
                        lines = [l.strip() for l in parent_text.split('\n') if l.strip()]
                        for line in lines:
                            if len(line) > 5 and any(c.isalpha() for c in line):
                                name = line
                                break
                        if name and len(name) > 3:
                            break
                    parent = getattr(parent, 'parent', None)
        
        # Build full URL
        if href.startswith('http'):
            url = href
        elif href.startswith('/'):
            url = f"https://www.vlr.gg{href}"
        else:
            url = f"https://www.vlr.gg/{href}"
        
        tournaments.append({
            'name': name or f"Tournament {event_id}",
            'url': url,
            'event_id': event_id
        })
    
    return tournaments


def detect_showmatch(match_name: str, tournament_name: str = '') -> bool:
    """
    Detect if a match is a showmatch based on match name and tournament name.
    
    Showmatches typically contain keywords like:
    - "Showmatch", "Show Match", "All-Star"
    - "Exhibition"
    - Sometimes in tournament names
    """
    text = f"{tournament_name} {match_name}".lower()
    
    showmatch_indicators = [
        'showmatch',
        'show match',
        'show-match',
        'all-star',
        'all star',
        'exhibition',
        'charity match',
        'fun match'
    ]
    
    return any(indicator in text for indicator in showmatch_indicators)


async def scrape_all_vct_matches(vct_2024_url: str = "https://www.vlr.gg/vct-2024",
                                 vct_2025_url: str = "https://www.vlr.gg/vct-2025") -> Dict[str, List[Tuple[int, str]]]:
    """
    Scrape all match IDs from all tournaments in VCT 2024 and 2025.
    
    Returns dict with keys:
    - 'vct_2024': List of (match_id, tournament_name) tuples
    - 'vct_2025': List of (match_id, tournament_name) tuples
    - 'showmatches': List of (match_id, tournament_name) tuples
    """
    from .tournament_scraper import scrape_tournament_match_ids
    
    results = {
        'vct_2024': [],
        'vct_2025': [],
        'showmatches': []
    }
    
    # Scrape VCT 2024 tournaments
    print(f"Scraping VCT 2024 tournaments from {vct_2024_url}...")
    vct_2024_tournaments = await scrape_vct_tournaments(vct_2024_url)
    print(f"Found {len(vct_2024_tournaments)} tournaments in VCT 2024")
    
    for i, tournament in enumerate(vct_2024_tournaments, 1):
        print(f"  [{i}/{len(vct_2024_tournaments)}] Scraping {tournament['name']}...")
        try:
            match_ids = await scrape_tournament_match_ids(tournament['url'], completed_only=True)
            for match_id in match_ids:
                results['vct_2024'].append((match_id, tournament['name']))
            print(f"    Found {len(match_ids)} completed matches")
        except Exception as e:
            print(f"    Error: {e}")
    
    # Scrape VCT 2025 tournaments
    print(f"\nScraping VCT 2025 tournaments from {vct_2025_url}...")
    vct_2025_tournaments = await scrape_vct_tournaments(vct_2025_url)
    print(f"Found {len(vct_2025_tournaments)} tournaments in VCT 2025")
    
    for i, tournament in enumerate(vct_2025_tournaments, 1):
        print(f"  [{i}/{len(vct_2025_tournaments)}] Scraping {tournament['name']}...")
        try:
            match_ids = await scrape_tournament_match_ids(tournament['url'], completed_only=True)
            for match_id in match_ids:
                results['vct_2025'].append((match_id, tournament['name']))
            print(f"    Found {len(match_ids)} completed matches")
        except Exception as e:
            print(f"    Error: {e}")
    
    return results


async def classify_matches(match_ids_with_names: List[Tuple[int, str]]) -> Dict[str, List[int]]:
    """
    Classify matches into VCT, SHOWMATCH, etc. by scraping match pages.
    
    Returns dict with 'vct' and 'showmatch' lists of match IDs.
    """
    from .vlr_ingest import scrape_match
    
    classified = {
        'vct': [],
        'showmatch': []
    }
    
    print(f"\nClassifying {len(match_ids_with_names)} matches...")
    
    for i, (match_id, tournament_name) in enumerate(match_ids_with_names, 1):
        if i % 50 == 0:
            print(f"  Progress: {i}/{len(match_ids_with_names)}")
        
        try:
            match_row, _, _ = await scrape_match(match_id)
            match_name = match_row[4] if len(match_row) > 4 else ''
            
            if detect_showmatch(match_name, tournament_name):
                classified['showmatch'].append(match_id)
            else:
                classified['vct'].append(match_id)
        except Exception as e:
            # On error, default to VCT
            print(f"    Warning: Error classifying match {match_id}: {e}")
            classified['vct'].append(match_id)
    
    return classified
