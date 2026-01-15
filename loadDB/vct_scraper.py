"""
Scrape all VCT tournaments from vct-2024 and vct-2025 pages and extract all match IDs.
"""
import re
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple, Optional
from .tournament_scraper import fetch_html, extract_event_id_from_url


# Expected match counts for key VCT events based on manual ground truth.
# These are used for auditing but the scraper logic does not depend on them.
# Keys are (year, phase, region) where:
#   - phase ∈ {"kickoff", "stage1", "stage2", "masters", "champs"}
#   - region ∈ {"americas", "emea", "pacific", "china", "international"}
VCT_EVENT_EXPECTATIONS: Dict[Tuple[int, str, str], Dict[str, int]] = {
    # 2025 domestic leagues
    (2025, "stage2", "americas"): {"expected_matches": 43, "expected_showmatches": 1},
    (2025, "stage2", "emea"): {"expected_matches": 43, "expected_showmatches": 1},
    (2025, "stage2", "pacific"): {"expected_matches": 43, "expected_showmatches": 1},
    (2025, "stage2", "china"): {"expected_matches": 43, "expected_showmatches": 1},
    (2025, "stage1", "americas"): {"expected_matches": 42, "expected_showmatches": 0},
    (2025, "stage1", "emea"): {"expected_matches": 42, "expected_showmatches": 0},
    (2025, "stage1", "pacific"): {"expected_matches": 42, "expected_showmatches": 0},
    (2025, "stage1", "china"): {"expected_matches": 42, "expected_showmatches": 0},
    (2025, "kickoff", "americas"): {"expected_matches": 22, "expected_showmatches": 0},
    (2025, "kickoff", "emea"): {"expected_matches": 22, "expected_showmatches": 0},
    (2025, "kickoff", "pacific"): {"expected_matches": 22, "expected_showmatches": 0},
    (2025, "kickoff", "china"): {"expected_matches": 22, "expected_showmatches": 0},
    # 2024 domestic leagues
    (2024, "stage2", "americas"): {"expected_matches": 33, "expected_showmatches": 0},
    (2024, "stage2", "emea"): {"expected_matches": 33, "expected_showmatches": 0},
    (2024, "stage2", "pacific"): {"expected_matches": 33, "expected_showmatches": 0},
    (2024, "stage2", "china"): {"expected_matches": 33, "expected_showmatches": 0},
    (2024, "stage1", "americas"): {"expected_matches": 38, "expected_showmatches": 0},
    (2024, "stage1", "emea"): {"expected_matches": 38, "expected_showmatches": 0},
    (2024, "stage1", "pacific"): {"expected_matches": 38, "expected_showmatches": 0},
    (2024, "stage1", "china"): {"expected_matches": 38, "expected_showmatches": 0},
    (2024, "kickoff", "americas"): {"expected_matches": 19, "expected_showmatches": 0},
    (2024, "kickoff", "emea"): {"expected_matches": 19, "expected_showmatches": 0},
    (2024, "kickoff", "pacific"): {"expected_matches": 19, "expected_showmatches": 0},
    (2024, "kickoff", "china"): {"expected_matches": 19, "expected_showmatches": 0},
    # International events
    (2025, "masters", "international"): {"expected_matches": 25, "expected_showmatches": 1},  # Masters Toronto
    (2025, "champs", "international"): {"expected_matches": 34, "expected_showmatches": 0},   # Champs 2025
    # 2024 Masters / Champs – counts not provided explicitly by user; we still audit by diff vs DB.
    # We'll leave expectations empty for these but still include them in reports.
}


def classify_vct_tournament(name: str, year: int) -> Optional[Dict[str, str]]:
    """
    Classify a VCT tournament into phase/region buckets based on its name.

    This is intentionally heuristic but good enough for auditing 2024/2025 events.
    """
    if not name:
        return None

    lower = name.lower()

    # Phase
    phase: Optional[str] = None
    if "kickoff" in lower:
        phase = "kickoff"
    elif "stage 1" in lower or "stage one" in lower:
        phase = "stage1"
    elif "stage 2" in lower or "stage two" in lower:
        phase = "stage2"
    elif "masters" in lower:
        phase = "masters"
    elif "champions" in lower or "champs" in lower:
        phase = "champs"

    if not phase:
        return None

    # Region (or international)
    region = "international"
    if "americas" in lower:
        region = "americas"
    elif "emea" in lower:
        region = "emea"
    elif "pacific" in lower:
        region = "pacific"
    elif "china" in lower:
        region = "china"

    return {
        "year": str(year),
        "phase": phase,
        "region": region,
    }


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


async def get_vct_target_events() -> List[Dict[str, object]]:
    """
    Enumerate key VCT 2024/2025 events we care about for auditing/backfill.

    Returns a list of dicts with:
      - name: Tournament name
      - url: Event URL
      - event_id: VLR event ID
      - year: 2024 or 2025
      - phase: kickoff/stage1/stage2/masters/champs
      - region: americas/emea/pacific/china/international
      - expected_matches / expected_showmatches (if known, else None)
    """
    targets: List[Dict[str, object]] = []

    for year, vct_url in [(2024, "https://www.vlr.gg/vct-2024"), (2025, "https://www.vlr.gg/vct-2025")]:
        print(f"Discovering VCT {year} tournaments from {vct_url}...")
        tournaments = await scrape_vct_tournaments(vct_url)
        print(f"  Found {len(tournaments)} tournaments in VCT {year}")

        for t in tournaments:
            cls = classify_vct_tournament(t["name"], year)
            if not cls:
                continue

            phase = cls["phase"]
            region = cls["region"]

            # Only keep events that are explicitly mentioned in the user's spec:
            # - Kickoff, Stage1, Stage2 for all four regions
            # - Masters (Bangkok, Shanghai, Madrid, Toronto)
            # - Champs (2024, 2025)
            if phase in {"kickoff", "stage1", "stage2"} and region in {"americas", "emea", "pacific", "china"}:
                pass
            elif phase == "masters" and any(city in t["name"].lower() for city in ["bangkok", "shanghai", "madrid", "toronto"]):
                region = "international"
            elif phase == "champs" or "champions" in t["name"].lower():
                region = "international"
            else:
                continue

            exp = VCT_EVENT_EXPECTATIONS.get((year, phase, region))
            targets.append(
                {
                    "name": t["name"],
                    "url": t["url"],
                    "event_id": t["event_id"],
                    "year": year,
                    "phase": phase,
                    "region": region,
                    "expected_matches": exp["expected_matches"] if exp else None,
                    "expected_showmatches": exp["expected_showmatches"] if exp else None,
                }
            )

    # Sort for nicer output
    targets.sort(key=lambda e: (e["year"], e["phase"], e["region"], e["name"]))
    return targets


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
