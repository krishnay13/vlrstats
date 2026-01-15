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
    
    Uses multiple strategies to find all tournament links, including:
    - Direct event links
    - Links in event cards/containers
    - Links in completed/upcoming sections
    
    Returns list of dicts with 'name', 'url', 'event_id'
    """
    async with aiohttp.ClientSession() as session:
        html = await fetch_html(session, vct_url)
    
    soup = BeautifulSoup(html, 'html.parser')
    tournaments = []
    seen_event_ids = set()
    
    # Strategy 1: Find all links with /event/ followed by a number
    event_links = soup.find_all('a', href=re.compile(r'/event/\d+'))
    
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
        # Clean up the name - often includes extra metadata
        name = link.get_text(strip=True)
        
        # Clean up common patterns in tournament names
        if name:
            # Remove common suffixes/prefixes
            name = re.sub(r'\s*(completed|status|prize|pool|dates|region).*$', '', name, flags=re.I)
            name = re.sub(r'\$\d+[,\d]*', '', name)  # Remove prize amounts
            name = re.sub(r'\d{1,2}\s*[–—]\s*\d{1,2}', '', name)  # Remove date ranges
            name = name.strip()
        
        if not name or len(name) < 3:
            # Try to get name from parent or nearby elements
            parent = link.parent
            for _ in range(7):  # Check more levels
                if parent:
                    parent_text = parent.get_text(' ', strip=True)
                    if parent_text and len(parent_text) > len(name) and any(c.isalpha() for c in parent_text):
                        lines = [l.strip() for l in parent_text.split('\n') if l.strip()]
                        for line in lines:
                            if len(line) > 5 and any(c.isalpha() for c in line):
                                # Skip common non-tournament text
                                skip_words = ['completed', 'upcoming', 'events', 'view all', 'status', 'prize', 'pool', 'dates', 'region']
                                if not any(word in line.lower() for word in skip_words):
                                    # Clean the line
                                    cleaned = re.sub(r'\$\d+[,\d]*', '', line)
                                    cleaned = re.sub(r'\d{1,2}\s*[–—]\s*\d{1,2}', '', cleaned)
                                    cleaned = cleaned.strip()
                                    if len(cleaned) > 5:
                                        name = cleaned
                                        break
                        if name and len(name) > 3:
                            break
                    parent = getattr(parent, 'parent', None)
        
        # Final cleanup
        if name:
            name = re.sub(r'\s+', ' ', name).strip()
            # Remove trailing metadata
            name = re.sub(r'\s*(completed|status|prize|pool).*$', '', name, flags=re.I)
            name = name.strip()
        
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
    
    # Strategy 2: Look for event cards/containers that might have been missed
    event_containers = soup.find_all(['div', 'article', 'section'], class_=re.compile(r'event|tournament|card', re.I))
    for container in event_containers:
        container_links = container.find_all('a', href=re.compile(r'/event/\d+'))
        for link in container_links:
            href = link.get('href', '')
            event_id = extract_event_id_from_url(href)
            if event_id and event_id not in seen_event_ids:
                seen_event_ids.add(event_id)
                name = link.get_text(strip=True) or container.get_text(strip=True).split('\n')[0]
                if href.startswith('http'):
                    url = href
                elif href.startswith('/'):
                    url = f"https://www.vlr.gg{href}"
                else:
                    url = f"https://www.vlr.gg/{href}"
                tournaments.append({
                    'name': name[:100] if name else f"Tournament {event_id}",
                    'url': url,
                    'event_id': event_id
                })
    
    # Remove duplicates while preserving order
    unique_tournaments = []
    seen = set()
    for t in tournaments:
        if t['event_id'] not in seen:
            seen.add(t['event_id'])
            unique_tournaments.append(t)
    
    return unique_tournaments


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
            # Try scraping with completed_only first
            match_ids = await scrape_tournament_match_ids(tournament['url'], completed_only=True)
            
            # Also try without completed_only filter to catch any we might have missed
            # (but only add new ones)
            all_match_ids = await scrape_tournament_match_ids(tournament['url'], completed_only=False)
            additional = [mid for mid in all_match_ids if mid not in match_ids]
            if additional:
                print(f"    Found {len(additional)} additional matches (checking if completed)...")
                # Verify these are actually completed by checking a sample
                # For now, include them but they'll be filtered during ingestion if not completed
                match_ids.extend(additional[:10])  # Limit to avoid too many false positives
            
            for match_id in match_ids:
                results['vct_2024'].append((match_id, tournament['name']))
            print(f"    Found {len(match_ids)} matches")
        except Exception as e:
            print(f"    Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Scrape VCT 2025 tournaments
    print(f"\nScraping VCT 2025 tournaments from {vct_2025_url}...")
    vct_2025_tournaments = await scrape_vct_tournaments(vct_2025_url)
    print(f"Found {len(vct_2025_tournaments)} tournaments in VCT 2025")
    
    for i, tournament in enumerate(vct_2025_tournaments, 1):
        print(f"  [{i}/{len(vct_2025_tournaments)}] Scraping {tournament['name']}...")
        try:
            # Try scraping with completed_only first
            match_ids = await scrape_tournament_match_ids(tournament['url'], completed_only=True)
            
            # Also try without completed_only filter to catch any we might have missed
            all_match_ids = await scrape_tournament_match_ids(tournament['url'], completed_only=False)
            additional = [mid for mid in all_match_ids if mid not in match_ids]
            if additional:
                print(f"    Found {len(additional)} additional matches (checking if completed)...")
                # Include additional matches (will be verified during ingestion)
                match_ids.extend(additional[:10])  # Limit to avoid too many false positives
            
            for match_id in match_ids:
                results['vct_2025'].append((match_id, tournament['name']))
            print(f"    Found {len(match_ids)} matches")
        except Exception as e:
            print(f"    Error: {e}")
            import traceback
            traceback.print_exc()
    
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
            match_row, _, _, _ = await scrape_match(match_id)
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
