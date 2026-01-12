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
    """Extract tournament slug from URL for building matches URL"""
    # Try to get slug from URL like /event/2792/challengers-2026-spain-rising-split-1
    m = re.search(r'/event/\d+/([^/?]+)', url)
    return m.group(1) if m else None


async def fetch_html(session: aiohttp.ClientSession, url: str) -> str:
    """Fetch HTML from a URL with proper headers"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
        'Referer': 'https://www.vlr.gg/'
    }
    async with session.get(url, timeout=20, headers=headers) as resp:
        resp.raise_for_status()
        return await resp.text()


async def get_tournament_matches_url(event_url: str) -> str:
    """Build the matches URL for a tournament event page"""
    event_id = extract_event_id_from_url(event_url)
    if not event_id:
        raise ValueError(f"Could not extract event ID from URL: {event_url}")
    
    # First, try to get the tournament slug from the event page
    async with aiohttp.ClientSession() as session:
        html = await fetch_html(session, event_url)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try to find a link to the matches page (look for "Matches" tab/link)
        matches_links = soup.find_all('a', href=re.compile(r'/event/matches/' + event_id))
        for matches_link in matches_links:
            href = matches_link.get('href', '')
            if href:
                if href.startswith('http'):
                    # Ensure it has series_id=all parameter
                    if 'series_id=all' not in href:
                        if '?' in href:
                            href += '&series_id=all'
                        else:
                            href += '?series_id=all'
                    return href
                elif href.startswith('/'):
                    full_url = f"https://www.vlr.gg{href}"
                    if 'series_id=all' not in full_url:
                        if '?' in full_url:
                            full_url += '&series_id=all'
                        else:
                            full_url += '?series_id=all'
                    return full_url
        
        # Try to extract slug from the current URL if it has one
        slug_match = re.search(r'/event/\d+/([^/?]+)', event_url)
        if slug_match:
            slug = slug_match.group(1)
            return f"https://www.vlr.gg/event/matches/{event_id}/{slug}/?series_id=all"
        
        # Fallback: try to extract slug from page title or h1
        title_elem = soup.find('h1') or soup.find('title')
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            # Try to create a slug from the title
            # Remove special characters and convert to lowercase
            slug = re.sub(r'[^a-z0-9\s-]+', '', title_text.lower())
            slug = re.sub(r'\s+', '-', slug).strip('-')
            if slug and len(slug) > 3:  # Only use if it looks reasonable
                return f"https://www.vlr.gg/event/matches/{event_id}/{slug}/?series_id=all"
        
        # Last resort: try simple URL pattern (similar to retrieve_urls.py approach)
        return f"https://www.vlr.gg/event/matches/{event_id}/?series_id=all"


async def scrape_tournament_match_ids(event_url: str, completed_only: bool = True) -> List[int]:
    """
    Scrape all match IDs from a tournament matches page.
    
    Args:
        event_url: Tournament event URL (e.g., https://www.vlr.gg/event/2792)
        completed_only: If True, only return matches that are completed (have scores)
    
    Returns:
        List of match IDs (integers)
    """
    matches_url = await get_tournament_matches_url(event_url)
    
    async with aiohttp.ClientSession() as session:
        html = await fetch_html(session, matches_url)
    
    soup = BeautifulSoup(html, 'html.parser')
    match_ids: List[int] = []
    
    # Find all links that could be match links (pattern: /number/...)
    # Following the pattern from utilities/WebScraper/fetch.py
    all_links = soup.find_all('a', href=re.compile(r'/\d+/'))
    
    for link in all_links:
        href = link.get('href', '')
        # Extract match ID from URL like /123456/match-name
        # Following the pattern from fetch.py: parts[1].isdigit()
        parts = href.split('/')
        if len(parts) < 3 or not parts[1].isdigit():
            continue
            
        match_id = int(parts[1])
        
        # Skip if we've already seen this match ID
        if match_id in match_ids:
            continue
        
        # If we only want completed matches, check if the match has a score
        if completed_only:
            # Look for score indicators in the match item
            # Completed matches have scores like "2 : 0" or "1 : 1"
            # Upcoming matches have "–" (em dash)
            
            # Check the link's parent and siblings for score information
            parent = link.parent
            found_completed = False
            
            # Check up to 10 levels up the DOM tree
            for _ in range(10):
                if parent is None:
                    break
                
                # Get text from the container
                container_text = parent.get_text(' ', strip=True)
                
                # Look for score pattern: digits separated by : or -
                # But exclude time patterns (like "11:00 am")
                score_match = re.search(r'\b(\d{1,2})\s*[:\-]\s*(\d{1,2})\b', container_text)
                if score_match:
                    score1, score2 = int(score_match.group(1)), int(score_match.group(2))
                    # Valid match scores are typically 0-3
                    if 0 <= score1 <= 3 and 0 <= score2 <= 3:
                        # Check that it's not a time (has AM/PM) or date
                        if not re.search(r'\d{1,2}:\d{2}\s*(AM|PM|am|pm)', container_text):
                            # Check that it's not an upcoming match (has em dash)
                            if not re.search(r'[–—]\s*[–—]', container_text):
                                found_completed = True
                                match_ids.append(match_id)
                                break
                
                # Also check for explicit completion indicators
                if re.search(r'\b(Completed|Finished|Done|Result)\b', container_text, re.I):
                    found_completed = True
                    match_ids.append(match_id)
                    break
                
                # Check if there's a "Stats:" link (completed matches often have this)
                if link.get_text(strip=True) in ['Stats:', 'Stats']:
                    # Look for score in nearby text
                    if re.search(r'\d+\s*:\s*\d+', container_text):
                        if not re.search(r'[–—]\s*[–—]', container_text):
                            found_completed = True
                            match_ids.append(match_id)
                            break
                
                parent = getattr(parent, 'parent', None)
        else:
            # Include all matches
            match_ids.append(match_id)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_ids = []
    for mid in match_ids:
        if mid not in seen:
            seen.add(mid)
            unique_ids.append(mid)
    
    return unique_ids


def save_match_ids_to_file(match_ids: List[int], filename: str) -> None:
    """Save match IDs to a text file, one per line"""
    with open(filename, 'w', encoding='utf-8') as f:
        for match_id in match_ids:
            f.write(f"{match_id}\n")


def load_match_ids_from_file(filename: str) -> List[int]:
    """Load match IDs from a text file"""
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
