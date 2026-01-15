"""
Base scraping utilities for VLR.gg.

Provides common functionality for all scrapers:
- HTTP fetching with retry logic
- URL parsing and validation
"""
import re
import aiohttp
import asyncio
from typing import Optional


def match_id_from_url(url: str) -> Optional[int]:
    """
    Extract match ID from a VLR.gg URL.
    
    Args:
        url: URL containing a match ID (e.g., "https://www.vlr.gg/427991/match-name")
    
    Returns:
        Match ID as integer if found, None otherwise
    """
    m = re.search(r"/([0-9]+)/", url)
    return int(m.group(1)) if m else None


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
