"""
Main ingestion pipeline.

Orchestrates the complete ingestion process:
1. Scrapes match data from URLs
2. Applies normalization (aliases)
3. Validates data
4. Inserts into database
"""
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import List, Optional, Tuple
from dataclasses import dataclass

from ..scrapers.base import fetch_html, match_id_from_url
from ..scrapers.match import extract_match_metadata
from ..scrapers.maps import extract_maps
from ..scrapers.players import extract_player_stats
from ..normalizers.team import normalize_team
from ..normalizers.tournament import normalize_tournament
from ..normalizers.match_type import normalize_match_type
from ..db_utils import get_conn, ensure_matches_columns, upsert_match, upsert_maps, upsert_player_stats
from .validator import validate_match_data


@dataclass
class IngestionResult:
    """Result of ingestion operation."""
    success_count: int
    error_count: int
    skipped_count: int = 0
    warnings: List[str] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []


async def scrape_and_normalize_match(url: str) -> tuple:
    """
    Scrape a match and apply normalization.
    
    Args:
        url: Match URL
    
    Returns:
        Tuple of (match_metadata_dict, maps_info, players_info, match_type)
    """
    # Get match ID
    match_id = match_id_from_url(url)
    if not match_id:
        # Try constructing URL if just ID provided
        if isinstance(url, int) or (isinstance(url, str) and url.isdigit()):
            url = f"https://www.vlr.gg/{url}"
            match_id = match_id_from_url(url)
        else:
            raise ValueError(f"Could not extract match ID from URL: {url}")
    
    # Fetch and parse HTML
    async with aiohttp.ClientSession() as session:
        html = await fetch_html(session, url)
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract match metadata directly from the page
    match_meta = extract_match_metadata(soup, match_id, url)
    
    # Normalize entities using aliases
    match_meta['team_a'] = normalize_team(match_meta['team_a'])
    match_meta['team_b'] = normalize_team(match_meta['team_b'])
    match_meta['tournament'] = normalize_tournament(match_meta['tournament'])
    
    # Detect match type
    match_type = None
    if match_meta['is_showmatch']:
        match_type = 'SHOWMATCH'
    else:
        tournament_lower = (match_meta['tournament'] or '').lower()
        if 'vct' in tournament_lower or 'champions tour' in tournament_lower:
            match_type = 'VCT'
        elif 'vcl' in tournament_lower or 'challengers' in tournament_lower:
            match_type = 'VCL'
        elif 'offseason' in tournament_lower:
            match_type = 'OFFSEASON'
        else:
            match_type = 'VCT'  # Default
    
    match_type = normalize_match_type(match_type)
    
    # Extract maps (normalization happens in extract_maps)
    maps_info = extract_maps(soup, match_id, match_meta['team_a'], match_meta['team_b'])
    
    # Extract player stats (normalization happens in extract_player_stats)
    players_info = extract_player_stats(soup, match_id)
    
    # Build match row tuple for database
    match_result = f"{match_meta['team_a']} {match_meta['team_a_score']}-{match_meta['team_b_score']} {match_meta['team_b']}"
    match_row = (
        match_id,
        match_meta['tournament'],
        match_meta['stage'],
        match_type,
        match_meta['match_name'],
        match_meta['team_a'],
        match_meta['team_b'],
        match_meta['team_a_score'],
        match_meta['team_b_score'],
        match_result,
        match_meta['match_ts_utc'],
        match_meta['match_date'],
        match_meta.get('bans_picks'),
    )
    
    return match_row, maps_info, players_info


async def ingest_from_urls(
    urls: List[str] | List[Tuple[str, Optional[str]]],
    validate: bool = True,
    match_type: Optional[str] = None
) -> IngestionResult:
    """
    Main ingestion pipeline that processes URLs and inserts into database.
    
    Match type logic:
    - VCT = Tier 1 Valorant (entire tournament is tier 1, but may contain showmatches)
    - VCL = Tier 2 Valorant (entire tournament is tier 2)
    - OFFSEASON = May mix tier 1 and tier 2 teams
    - SHOWMATCH = Always filtered out (even if within VCT/VCL tournaments)
    
    Args:
        urls: List of match URLs (or IDs), or list of tuples (url, match_type)
        validate: If True, validate data before inserting
        match_type: Optional global match type override (overrides per-URL types)
                   Use VCT/VCL/OFFSEASON to indicate tournament tier
    
    Returns:
        IngestionResult with success/error counts and warnings
    """
    conn = get_conn()
    ensure_matches_columns(conn)
    
    success_count = 0
    error_count = 0
    skipped_count = 0
    warnings = []
    errors = []
    
    # Normalize urls to list of tuples
    url_tuples = []
    for item in urls:
        if isinstance(item, tuple):
            url_tuples.append(item)
        else:
            url_tuples.append((item, None))
    
    for url, url_match_type in url_tuples:
        try:
            # Use global override if provided, otherwise use per-URL type
            effective_match_type = match_type or url_match_type
            
            # Scrape and normalize
            match_row, maps_info, players_info = await scrape_and_normalize_match(url)
            match_id = match_row[0]
            detected_match_type = match_row[3] if len(match_row) > 3 else None
            
            # ALWAYS skip showmatches, regardless of specified type
            # Showmatches can exist within VCT/VCL tournaments but should be filtered
            if detected_match_type == 'SHOWMATCH':
                skipped_count += 1
                print(f"Skipping showmatch: {url} (match_id: {match_id})")
                continue
            
            # If user specified a match type, use it (unless it was SHOWMATCH, which we already filtered)
            # Otherwise, use the auto-detected type
            final_match_type = None
            if effective_match_type and effective_match_type.upper() != 'SHOWMATCH':
                # User specified a valid type (VCT/VCL/OFFSEASON)
                final_match_type = normalize_match_type(effective_match_type)
            elif detected_match_type and detected_match_type != 'SHOWMATCH':
                # Use auto-detected type (already normalized)
                final_match_type = detected_match_type
            else:
                # Fallback: default to VCT if unclear
                final_match_type = 'VCT'
            
            # Update match row with final match type
            match_row_list = list(match_row)
            match_row_list[3] = final_match_type
            match_row = tuple(match_row_list)
            
            # Validate if requested
            if validate:
                is_valid, match_warnings = validate_match_data(match_row, maps_info, players_info)
                if match_warnings:
                    warnings.extend([f"Match {match_id}: {w}" for w in match_warnings])
            
            # Insert into database
            upsert_match(conn, match_row)
            m_lookup = upsert_maps(conn, maps_info)
            upsert_player_stats(conn, players_info, m_lookup)
            conn.commit()
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            error_msg = f"Error ingesting {url}: {e}"
            errors.append(error_msg)
            print(error_msg)
            import traceback
            traceback.print_exc()
            continue
    
    conn.close()
    
    if skipped_count > 0:
        print(f"Skipped {skipped_count} showmatch(es)")
    
    return IngestionResult(
        success_count=success_count,
        error_count=error_count,
        skipped_count=skipped_count,
        warnings=warnings,
        errors=errors
    )
