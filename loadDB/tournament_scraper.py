import re
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import List


def extract_event_id_from_url(url: str) -> str | None:
    """Extract event ID from a tournament URL like https://www.vlr.gg/event/2792"""
    m = re.search(r'/event/(\d+)', url)
    return m.group(1) if m else None


def extract_tournament_slug_from_url(url: str) -> str | None:
    """
    Extract tournament slug from URL for building matches URL.
    
    Args:
        url: Tournament URL (e.g., /event/2792/challengers-2026-spain-rising-split-1)
    
    Returns:
        Tournament slug if found, None otherwise
    """
    m = re.search(r'/event/\d+/([^/?]+)', url)
    return m.group(1) if m else None


async def fetch_html(session: aiohttp.ClientSession, url: str, max_retries: int = 3) -> str:
    """
    Fetch HTML from a URL with proper headers to mimic browser requests.
    Includes retry logic for transient failures.
    
    Args:
        session: aiohttp client session
        url: URL to fetch
        max_retries: Maximum number of retry attempts (default: 3)
    
    Returns:
        HTML content as string
    
    Raises:
        aiohttp.ClientError: If the request fails after all retries
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
        'Referer': 'https://www.vlr.gg/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    last_error = None
    for attempt in range(max_retries):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30), headers=headers) as resp:
                # Handle rate limiting
                if resp.status == 429:
                    wait_time = 2 ** attempt  # Exponential backoff
                    await asyncio.sleep(wait_time)
                    continue
                
                resp.raise_for_status()
                return await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                await asyncio.sleep(wait_time)
            else:
                raise
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
            else:
                raise
    
    # Should never reach here, but just in case
    if last_error:
        raise last_error
    raise aiohttp.ClientError(f"Failed to fetch {url} after {max_retries} attempts")


async def get_tournament_matches_url(event_url: str) -> str:
    """
    Build the matches URL for a tournament event page.
    
    Attempts multiple strategies to construct the matches URL:
    1. Find existing matches link on the event page
    2. Extract slug from the event URL
    3. Generate slug from page title
    4. Fallback to simple URL pattern
    
    Args:
        event_url: Tournament event URL (e.g., https://www.vlr.gg/event/2792)
    
    Returns:
        Full URL to the tournament matches page with series_id=all parameter
    
    Raises:
        ValueError: If event ID cannot be extracted from URL
    """
    event_id = extract_event_id_from_url(event_url)
    if not event_id:
        raise ValueError(f"Could not extract event ID from URL: {event_url}")
    
    async with aiohttp.ClientSession() as session:
        html = await fetch_html(session, event_url)
        soup = BeautifulSoup(html, 'html.parser')
        
        matches_links = soup.find_all('a', href=re.compile(r'/event/matches/' + event_id))
        for matches_link in matches_links:
            href = matches_link.get('href', '')
            if href:
                if href.startswith('http'):
                    if 'series_id=all' not in href:
                        href += '&series_id=all' if '?' in href else '?series_id=all'
                    return href
                elif href.startswith('/'):
                    full_url = f"https://www.vlr.gg{href}"
                    if 'series_id=all' not in full_url:
                        full_url += '&series_id=all' if '?' in full_url else '?series_id=all'
                    return full_url
        
        slug_match = re.search(r'/event/\d+/([^/?]+)', event_url)
        if slug_match:
            slug = slug_match.group(1)
            return f"https://www.vlr.gg/event/matches/{event_id}/{slug}/?series_id=all"
        
        title_elem = soup.find('h1') or soup.find('title')
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            slug = re.sub(r'[^a-z0-9\s-]+', '', title_text.lower())
            slug = re.sub(r'\s+', '-', slug).strip('-')
            if slug and len(slug) > 3:
                return f"https://www.vlr.gg/event/matches/{event_id}/{slug}/?series_id=all"
        
        return f"https://www.vlr.gg/event/matches/{event_id}/?series_id=all"


async def scrape_tournament_match_ids(event_url: str, completed_only: bool = True) -> List[int]:
    """
    Scrape all match IDs from a tournament matches page with multiple fallback strategies.
    
    Uses multiple strategies to find matches:
    1. Direct match links (pattern: /number/match-name)
    2. Match item containers
    3. Stats links
    4. All numeric links that could be matches
    
    When completed_only is True, validates matches by checking for score patterns.
    More lenient detection to catch all completed matches.
    
    Args:
        event_url: Tournament event URL (e.g., https://www.vlr.gg/event/2792)
        completed_only: If True, only return matches that are completed (have scores)
    
    Returns:
        List of unique match IDs (integers), preserving order
    """
    matches_url = await get_tournament_matches_url(event_url)
    
    async with aiohttp.ClientSession() as session:
        html = await fetch_html(session, matches_url)
    
    soup = BeautifulSoup(html, 'html.parser')
    match_ids: List[int] = []
    seen_ids = set()
    
    # Strategy 1: Find all links with numeric IDs (most common pattern)
    all_links = soup.find_all('a', href=re.compile(r'/\d+/'))
    
    for link in all_links:
        href = link.get('href', '')
        if not href:
            continue
            
        # Extract match ID - pattern: /123456/match-name or /123456/
        parts = href.split('/')
        if len(parts) < 2:
            continue
        
        # Check if second part is a digit (match ID)
        potential_id = parts[1] if len(parts) > 1 else None
        if not potential_id or not potential_id.isdigit():
            continue
        
        match_id = int(potential_id)
        
        # Skip if already seen
        if match_id in seen_ids:
            continue
        
        # Skip obviously wrong IDs (too small or too large)
        if match_id < 1000 or match_id > 9999999:
            continue
        
        # Check if this looks like a match link (has match name or is in match context)
        link_text = link.get_text(strip=True).lower()
        href_lower = href.lower()
        
        # Skip if it's clearly not a match (common non-match patterns)
        skip_patterns = ['/event/', '/team/', '/player/', '/stats/', '/rankings/', '/matches/']
        if any(pattern in href_lower for pattern in skip_patterns):
            continue
        
        # If completed_only, check if match is completed
        if completed_only:
            is_completed = False
            
            # Strategy A: Check for score in nearby text
            parent = link.parent
            for _ in range(15):  # Check up DOM tree
                if parent is None:
                    break
                
                container_text = parent.get_text(' ', strip=True)
                
                # Look for score pattern (e.g., "2 : 0", "1-1", "2-0")
                score_match = re.search(r'\b(\d{1,2})\s*[:\-]\s*(\d{1,2})\b', container_text)
                if score_match:
                    score1, score2 = int(score_match.group(1)), int(score_match.group(2))
                    # Valid match scores (0-3 for best-of-3, 0-5 for best-of-5)
                    if 0 <= score1 <= 5 and 0 <= score2 <= 5:
                        # Exclude time patterns
                        if not re.search(r'\d{1,2}:\d{2}\s*(AM|PM|am|pm|UTC|GMT)', container_text, re.I):
                            # Exclude upcoming matches (em dash)
                            if not re.search(r'[–—]\s*[–—]|TBD|Pending|Upcoming', container_text, re.I):
                                is_completed = True
                                break
                
                # Strategy B: Check for completion indicators
                if re.search(r'\b(Completed|Finished|Done|Result|Final)\b', container_text, re.I):
                    # Make sure it's not "Upcoming" or "Pending"
                    if not re.search(r'(Upcoming|Pending|TBD|Schedule)', container_text, re.I):
                        is_completed = True
                        break
                
                # Strategy C: Check if link text indicates completion
                if link_text in ['stats', 'stats:', 'view', 'result']:
                    # Check for score nearby
                    if re.search(r'\d+\s*[:\-]\s*\d+', container_text):
                        if not re.search(r'[–—]\s*[–—]', container_text):
                            is_completed = True
                            break
                
                parent = getattr(parent, 'parent', None)
            
            # Strategy D: If link is in a match item container, check the whole container
            if not is_completed:
                # Look for match item containers
                match_item = link
                for _ in range(5):
                    if match_item is None:
                        break
                    classes = match_item.get('class', []) if hasattr(match_item, 'get') else []
                    class_str = ' '.join(classes).lower() if classes else ''
                    if 'match' in class_str or 'item' in class_str:
                        item_text = match_item.get_text(' ', strip=True)
                        # If container has team names and scores, it's likely completed
                        if re.search(r'\d+\s*[:\-]\s*\d+', item_text):
                            if not re.search(r'[–—]\s*[–—]|TBD|Pending', item_text, re.I):
                                is_completed = True
                                break
                    match_item = getattr(match_item, 'parent', None)
            
            if is_completed:
                match_ids.append(match_id)
                seen_ids.add(match_id)
        else:
            # Include all matches
            match_ids.append(match_id)
            seen_ids.add(match_id)
    
    # Strategy 2: Look for match items in specific containers
    # Some pages structure matches differently
    match_containers = soup.find_all(['div', 'li', 'tr'], class_=re.compile(r'match|item', re.I))
    for container in match_containers:
        # Find all links in container
        container_links = container.find_all('a', href=re.compile(r'/\d+/'))
        for link in container_links:
            href = link.get('href', '')
            parts = href.split('/')
            if len(parts) >= 2 and parts[1].isdigit():
                match_id = int(parts[1])
                if match_id not in seen_ids and 1000 <= match_id <= 9999999:
                    if not completed_only:
                        match_ids.append(match_id)
                        seen_ids.add(match_id)
                    else:
                        # Check container for completion indicators
                        container_text = container.get_text(' ', strip=True)
                        if re.search(r'\d+\s*[:\-]\s*\d+', container_text):
                            if not re.search(r'[–—]\s*[–—]|TBD|Pending', container_text, re.I):
                                match_ids.append(match_id)
                                seen_ids.add(match_id)
    
    # Strategy 3: Look for data attributes that might contain match IDs
    data_elements = soup.find_all(attrs={'data-match-id': True}) + \
                   soup.find_all(attrs={'data-id': True})
    for elem in data_elements:
        match_id_str = elem.get('data-match-id') or elem.get('data-id')
        if match_id_str and match_id_str.isdigit():
            match_id = int(match_id_str)
            if match_id not in seen_ids and 1000 <= match_id <= 9999999:
                if not completed_only:
                    match_ids.append(match_id)
                    seen_ids.add(match_id)
                else:
                    # Check if completed
                    elem_text = elem.get_text(' ', strip=True)
                    if re.search(r'\d+\s*[:\-]\s*\d+', elem_text):
                        if not re.search(r'[–—]\s*[–—]|TBD|Pending', elem_text, re.I):
                            match_ids.append(match_id)
                            seen_ids.add(match_id)
    
    # Remove duplicates while preserving order
    return match_ids


def save_match_ids_to_file(match_ids: List[int], filename: str) -> None:
    """
    Save match IDs to a text file, one per line.
    
    Args:
        match_ids: List of match IDs to save
        filename: Path to output file
    """
    with open(filename, 'w', encoding='utf-8') as f:
        for match_id in match_ids:
            f.write(f"{match_id}\n")


def load_match_ids_from_file(filename: str) -> List[int]:
    """
    Load match IDs from a text file.
    
    Args:
        filename: Path to input file
    
    Returns:
        List of match IDs (empty list if file doesn't exist)
    """
    match_ids = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and line.isdigit():
                    match_ids.append(int(line))
    except FileNotFoundError:
        pass
    return match_ids
