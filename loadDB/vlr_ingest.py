"""
Compatibility wrapper for vlr_ingest module.

This module provides backward compatibility for code that imports from vlr_ingest.
The old monolithic implementation has been moved to _backup/vlr_ingest_old.py.

New code should use the modular ingestion pipeline from ingestion.pipeline.
"""
import asyncio
from typing import List, Optional

# Import new modular functions
from .scrapers.base import match_id_from_url, fetch_html
from .ingestion.pipeline import ingest_from_urls as _ingest_from_urls, scrape_and_normalize_match
from .ingestion.validator import validate_match_data as _validate_match_data


# Backward compatibility: provide scrape_match function
async def scrape_match(match_id_or_url: str | int):
    """
    Scrape match data from vlr.gg (backward compatibility wrapper).
    
    Args:
        match_id_or_url: Match ID (integer) or full URL string
    
    Returns:
        Tuple of (match_row, maps_info, players_info, is_showmatch)
    """
    url = f"https://www.vlr.gg/{match_id_or_url}" if isinstance(match_id_or_url, int) else str(match_id_or_url)
    
    # Use new pipeline function
    match_row, maps_info, players_info = await scrape_and_normalize_match(url)
    
    # Check if showmatch (from match_type in match_row)
    is_showmatch = match_row[3] == 'SHOWMATCH' if len(match_row) > 3 else False
    
    return match_row, maps_info, players_info, is_showmatch


# Backward compatibility: provide ingest_matches function
async def ingest_matches(
    ids_or_urls: List[str | int],
    match_type: Optional[str] = None,
    validate: bool = True
) -> None:
    """
    Ingest matches from vlr.gg into the database (backward compatibility wrapper).
    
    Note: Showmatches are automatically skipped and not inserted into the database.
    
    Args:
        ids_or_urls: List of match IDs (integers) or URLs (strings)
        match_type: Optional match type classification (VCT, VCL, OFFSEASON)
                   Note: SHOWMATCH is not allowed - showmatches are automatically skipped
        validate: If True, validate data before inserting (default: True)
    """
    # Reject SHOWMATCH match type
    if match_type and match_type.upper() == 'SHOWMATCH':
        print("Warning: SHOWMATCH match type is not allowed. Showmatches are automatically skipped.")
        match_type = None
    
    # Convert to URLs if needed
    urls = []
    for item in ids_or_urls:
        if isinstance(item, int):
            urls.append(f"https://www.vlr.gg/{item}")
        elif isinstance(item, str) and item.isdigit():
            urls.append(f"https://www.vlr.gg/{item}")
        else:
            urls.append(str(item))
    
    # Use new pipeline (automatically skips showmatches)
    result = await _ingest_from_urls(urls, validate=validate, match_type=match_type)
    
    # Print results for backward compatibility
    if result.success_count > 0 or result.error_count > 0:
        print(f"Ingestion complete: {result.success_count} successful, {result.error_count} errors")
    
    # Automatically recalculate ELO snapshots for 2026 and all-time after ingestion
    if result.success_count > 0:
        print("\nRecalculating ELO snapshots...")
        from .elo import compute_elo_snapshots
        compute_elo_snapshots()


# Backward compatibility: provide synchronous ingest function
def ingest(ids_or_urls: List[str | int], match_type: Optional[str] = None) -> None:
    """
    Synchronous wrapper for ingest_matches (backward compatibility).
    
    Args:
        ids_or_urls: List of match IDs (integers) or URLs (strings)
        match_type: Optional match type classification (VCT, VCL, OFFSEASON, SHOWMATCH)
    """
    asyncio.run(ingest_matches(ids_or_urls, match_type))
