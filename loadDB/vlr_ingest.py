import re
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from .db_utils import get_conn, ensure_matches_columns, upsert_match, upsert_maps, upsert_player_stats


def match_id_from_url(url: str) -> int | None:
    """
    Extract match ID from a VLR.gg URL.
    
    Args:
        url: URL containing a match ID (e.g., "https://www.vlr.gg/427991/match-name")
    
    Returns:
        Match ID as integer if found, None otherwise
    """
    m = re.search(r"/([0-9]+)/", url)
    return int(m.group(1)) if m else None


async def fetch_html(session: aiohttp.ClientSession, url: str) -> str:
    """
    Fetch HTML from a URL with proper headers to mimic browser requests.
    
    Args:
        session: aiohttp client session
        url: URL to fetch
    
    Returns:
        HTML content as string
    
    Raises:
        aiohttp.ClientError: If the request fails
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
        'Referer': 'https://www.vlr.gg/'
    }
    async with session.get(url, timeout=20, headers=headers) as resp:
        resp.raise_for_status()
        return await resp.text()


def _parse_dt_utc(soup: BeautifulSoup) -> str | None:
    """
    Parse UTC datetime from vlr.gg match page using multiple fallback strategies.
    
    Attempts to extract datetime in this order:
    1. Elements with data-utc-ts attribute (epoch integer or datetime string)
    2. Specific header selector (.match-header-date .moment-tz-convert)
    3. Time tags with datetime or data-datetime attributes
    4. Visible header text parsing
    
    Args:
        soup: BeautifulSoup parsed HTML
    
    Returns:
        ISO format datetime string with 'Z' suffix (UTC), or None if not found
    """
    any_ts = soup.select('[data-utc-ts]')
    for el in any_ts:
        val = el.get('data-utc-ts')
        if not val:
            continue
        try:
            ts = int(str(val).strip())
            return datetime.utcfromtimestamp(ts).isoformat() + 'Z'
        except Exception:
            pass
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M'):
            try:
                dt = datetime.strptime(val.strip(), fmt)
                return dt.isoformat() + 'Z'
            except Exception:
                continue
    t = soup.select_one('.match-header-date .moment-tz-convert')
    if t and t.has_attr('data-utc-ts'):
        tv = t['data-utc-ts']
        try:
            ts = int(str(tv).strip())
            return datetime.utcfromtimestamp(ts).isoformat() + 'Z'
        except Exception:
            pass
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M'):
            try:
                dt = datetime.strptime(str(tv).strip(), fmt)
                return dt.isoformat() + 'Z'
            except Exception:
                continue
    time_tags = soup.find_all('time')
    for tm in time_tags:
        val = tm.get('datetime') or tm.get('data-datetime')
        if val:
            try:
                if val.endswith('Z'):
                    return val
                return val + 'Z'
            except Exception:
                continue
    header = soup.select_one('.match-header-date') or soup.select_one('.match-header')
    if header:
        raw = header.get_text(' ', strip=True)
        for fmt in ("%b %d, %Y - %H:%M %Z", "%b %d, %Y - %H:%M", "%B %d, %Y"):
            try:
                dt = datetime.strptime(raw, fmt)
                return dt.isoformat() + 'Z'
            except Exception:
                continue
    return None


def _clean_map_name(text: str) -> str:
    """
    Normalize map name to a known canonical form.
    
    Args:
        text: Raw map name text from HTML
    
    Returns:
        Canonical map name if recognized, otherwise cleaned text
    """
    KNOWN = ['Ascent', 'Bind', 'Breeze', 'Fracture', 'Haven', 'Icebox', 'Lotus', 'Pearl', 'Split', 'Sunset', 'Abyss', 'Corrode']
    for km in KNOWN:
        if re.search(rf"\b{re.escape(km)}\b", text, re.IGNORECASE):
            return km
    return re.sub(r"\s+", " ", text).strip('- ').strip()


async def scrape_match(match_id_or_url: str | int) -> tuple[tuple, list[tuple], list[tuple]]:
    """
    Scrape match data from vlr.gg.
    
    Args:
        match_id_or_url: Match ID (integer) or full URL string
    
    Returns:
        Tuple of (match_row, maps_info, players_info):
        - match_row: Tuple with match metadata (match_id, tournament, stage, match_type, match_name, team_a, team_b, scores, result, match_ts_utc, match_date)
        - maps_info: List of tuples (match_id, game_id, map_name, team_a_score, team_b_score)
        - players_info: List of tuples (match_id, game_id, player, team, agent, rating, acs, kills, deaths, assists)
    """
    url = f"https://www.vlr.gg/{match_id_or_url}" if isinstance(match_id_or_url, int) else str(match_id_or_url)
    mid = match_id_from_url(url) if not isinstance(match_id_or_url, int) else match_id_or_url
    async with aiohttp.ClientSession() as session:
        html = await fetch_html(session, url)
    soup = BeautifulSoup(html, 'html.parser')

    teams = soup.select('.match-header-link-name .wf-title-med')
    team_a = teams[0].get_text(strip=True) if len(teams) > 0 else 'Unknown'
    team_b = teams[1].get_text(strip=True) if len(teams) > 1 else 'Unknown'

    # Extract scores - handle case where there's a colon span in between
    score_spans = soup.select('.match-header-vs-score .js-spoiler span, .match-header-vs-score span')
    a_score = b_score = 0
    
    # Filter out colon spans and get numeric scores
    score_values = []
    for span in score_spans:
        text = span.get_text(strip=True)
        # Skip colon/spacer elements
        if text and text not in [':', '-', 'vs', 'vs.']:
            try:
                score_values.append(int(text))
            except ValueError:
                pass
    
    if len(score_values) >= 2:
        a_score, b_score = score_values[0], score_values[1]
    elif len(score_values) == 1:
        # Only one score found, might be incomplete
        a_score = score_values[0]
    
    # Fallback: try to extract from text directly
    if a_score == 0 and b_score == 0:
        score_container = soup.select_one('.match-header-vs-score')
        if score_container:
            score_text = score_container.get_text(' ', strip=True)
            # Look for pattern like "2:0" or "2 - 0"
            score_match = re.search(r'(\d+)\s*[:\-]\s*(\d+)', score_text)
            if score_match:
                try:
                    a_score = int(score_match.group(1))
                    b_score = int(score_match.group(2))
                except ValueError:
                    pass

    # Extract tournament and match info with multiple fallbacks
    match_name_elem = soup.select_one('.match-header-event')
    match_name = match_name_elem.get_text(' ', strip=True) if match_name_elem else ''
    
    # Fallback: try to get from page title or other elements
    if not match_name or len(match_name) < 5:
        title_elem = soup.find('title')
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            # Extract from title like "Team A vs Team B - Tournament Name | VLR.gg"
            if ' - ' in title_text:
                match_name = title_text.split(' - ')[0] + ' - ' + title_text.split(' - ')[1].split(' | ')[0]
            else:
                match_name = title_text.split(' | ')[0] if ' | ' in title_text else title_text
    
    # Final fallback
    if not match_name or len(match_name) < 5:
        match_name = url.split('/')[-1].replace('-', ' ').title()
    
    stage = ''
    tournament = ''
    
    # Parse tournament name from match_name
    # Format is usually: "Tournament Name: Stage: Match Type" or "Tournament Name: Match Type"
    parts = [p.strip() for p in match_name.split(':')]
    if parts:
        tournament = parts[0].strip()
    
    # Extract stage
    if len(parts) >= 2:
        # Try to find stage in the parts
        for part in parts[1:-1] if len(parts) > 2 else parts[1:]:
            stage_match = re.search(r'(Main Event|Group Stage|Swiss Stage|Playoffs|Knockout Stage|Stage\s*[12]|Kickoff|Regular Season)', part, re.IGNORECASE)
            if stage_match:
                stage = stage_match.group(1)
                break
            # If no specific stage found, use the part before the last one
            if part and not stage:
                stage = part
    
    # Fallback: try to get tournament from breadcrumbs or other page elements
    if not tournament or len(tournament) < 3:
        breadcrumb = soup.select_one('.breadcrumb, .wf-breadcrumb, nav[aria-label="Breadcrumb"]')
        if breadcrumb:
            breadcrumb_text = breadcrumb.get_text(' ', strip=True)
            # Look for tournament name in breadcrumb
            if 'VCT' in breadcrumb_text or 'Champions Tour' in breadcrumb_text:
                # Extract tournament name
                parts = breadcrumb_text.split()
                for i, part in enumerate(parts):
                    if 'VCT' in part or 'Champions' in part:
                        # Get next few words as tournament name
                        tournament = ' '.join(parts[i:min(i+5, len(parts))])
                        break

    # Parse date/time with multiple fallbacks
    dt_utc = _parse_dt_utc(soup)
    
    # If no timestamp found, try additional methods
    if not dt_utc:
        # Try to find date in match header
        date_elem = soup.select_one('.match-header-date, .match-date, time[datetime]')
        if date_elem:
            datetime_attr = date_elem.get('datetime') or date_elem.get('data-datetime') or date_elem.get('data-utc-ts')
            if datetime_attr:
                        try:
                            # Try to parse various formats
                            from datetime import datetime
                            for fmt in ['%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                                try:
                                    dt = datetime.strptime(datetime_attr.strip(), fmt)
                                    parsed_dt = dt.isoformat()
                                    if not parsed_dt.endswith('Z'):
                                        parsed_dt += 'Z'
                                    dt_utc = parsed_dt
                                    break
                                except:
                                    continue
                        except:
                            pass
    
    date_str = dt_utc[:10] if dt_utc else None
    
    # Ensure we have at least a date - if not, log warning but continue
    if not date_str and not dt_utc:
        # Try to extract from URL or other sources as last resort
        pass  # Will be None, but match will still be saved

    maps_info: list[tuple] = []
    players_info: list[tuple] = []
    for game_div in soup.select('div.vm-stats-game'):
        game_id = game_div.get('data-game-id')
        if not game_id or game_id == 'all':
            continue
        header = game_div.find('div', class_='vm-stats-game-header')
        map_name = None
        if header:
            name_elem = header.find(class_='map')
            if name_elem:
                map_name = name_elem.get_text(strip=True)
        if not map_name:
            nav_item = soup.find('a', class_='vm-stats-gamesnav-item', attrs={'data-game-id': game_id})
            map_name = nav_item.get_text(strip=True) if nav_item else 'Unknown'
        map_name = _clean_map_name(map_name or 'Unknown')

        a_map_score = b_map_score = None
        if header:
            header_text = header.get_text(' ', strip=True)
            # Try multiple patterns for map scores
            # Pattern 1: "13 TeamA ... TeamB ... 8" (scores at start and end)
            # Pattern 2: "13 - 8" or "13:8" (dash or colon)
            # Pattern 3: "TeamA 13 TeamB 8" (scores after team names)
            
            # First try dash/colon pattern
            m = re.search(r'(\d{1,2})\s*[:\-]\s*(\d{1,2})', header_text)
            if m:
                try:
                    score1, score2 = int(m.group(1)), int(m.group(2))
                    # Valid map scores (0-13 for Valorant)
                    if 0 <= score1 <= 13 and 0 <= score2 <= 13:
                        a_map_score, b_map_score = score1, score2
                except Exception:
                    pass
            
            # If no dash pattern, try extracting from structure
            # Look for pattern like "13 TeamA ... TeamB ... 8" or "TeamA 13 ... TeamB 8"
            if a_map_score is None or b_map_score is None:
                # Extract all numbers from header
                numbers = re.findall(r'\b(\d{1,2})\b', header_text)
                # Filter out time patterns (like 1:02:40) and small numbers that are likely round-by-round
                valid_scores = []
                for num_str in numbers:
                    num = int(num_str)
                    # Valid map scores are typically 0-13
                    if 0 <= num <= 13:
                        valid_scores.append(num)
                
                # If we found 2 valid scores, use them
                # Usually the first and last valid scores are the map scores
                if len(valid_scores) >= 2:
                    # Try to find scores near team names or at start/end
                    # For now, use first and last valid scores
                    a_map_score, b_map_score = valid_scores[0], valid_scores[-1]
                elif len(valid_scores) == 1:
                    # Only one score found, might be incomplete
                    a_map_score = valid_scores[0]

        if a_map_score is not None and b_map_score is not None:
            maps_info.append((mid, game_id, map_name, a_map_score, b_map_score))

        if a_map_score is None or b_map_score is None:
            continue
        for row in game_div.select('table.wf-table-inset tbody tr'):
            cells = row.find_all('td')
            if len(cells) < 7:
                continue
            player_cell = cells[0]
            player = (player_cell.find('div', class_='text-of') or {}).get_text(strip=True) if player_cell else None
            team = (player_cell.find('div', class_='ge-text-light') or {}).get_text(strip=True) if player_cell else None
            img = row.find('img')
            agent = (img.get('title') or img.get('alt')) if img else None

            def first_num(text, default=0.0, as_int=False):
                text = (text or '').strip()
                parts = text.split()
                for part in parts:
                    cleaned = ''.join(c for c in part if c.isdigit() or c in '.-')
                    if cleaned and cleaned not in '.-':
                        try:
                            val = float(cleaned)
                            return int(val) if as_int else val
                        except Exception:
                            continue
                return default

            rating = first_num(cells[2].get_text(), 0.0)
            acs = first_num(cells[3].get_text(), 0, as_int=True)
            kills = first_num(cells[4].get_text(), 0, as_int=True)
            deaths = first_num(cells[5].get_text(), 0, as_int=True)
            assists = first_num(cells[6].get_text(), 0, as_int=True)
            if player:
                players_info.append((mid, game_id, player, team or 'Unknown', agent or 'Unknown', rating, acs, kills, deaths, assists))

    if any(tas is not None and tbs is not None for _, _, _, tas, tbs in maps_info):
        a_w = sum(1 for _, _, _, tas, tbs in maps_info if tas is not None and tbs is not None and tas > tbs)
        b_w = sum(1 for _, _, _, tas, tbs in maps_info if tas is not None and tbs is not None and tbs > tas)
        if (a_score + b_score) < 2 or (a_score + b_score) != (a_w + b_w):
            a_score, b_score = a_w, b_w

    match_row = (
        mid, tournament, stage, '', match_name,
        team_a, team_b, a_score, b_score, f"{team_a} {a_score}-{b_score} {team_b}", dt_utc, date_str
    )
    return match_row, maps_info, players_info


def _detect_showmatch(match_name: str, tournament: str = '') -> bool:
    """
    Detect if a match is a showmatch based on match name only.
    
    Only checks the match name/title for "showmatch" - not tournament name.
    
    Args:
        match_name: Name/title of the match
        tournament: Tournament name (not used, kept for compatibility)
    
    Returns:
        True if match name contains "showmatch", False otherwise
    """
    if not match_name:
        return False
    
    # Only check match name, not tournament name
    match_name_lower = match_name.lower()
    # Check for "showmatch" (with or without space/hyphen)
    return 'showmatch' in match_name_lower or 'show match' in match_name_lower or 'show-match' in match_name_lower


async def ingest_matches(ids_or_urls: list[str | int], match_type: str | None = None) -> None:
    """
    Ingest matches from vlr.gg into the database.
    
    Auto-detects match type (VCT/VCL/OFFSEASON/SHOWMATCH) if not provided by analyzing
    tournament name and match name for showmatch indicators.
    
    Args:
        ids_or_urls: List of match IDs (integers) or URLs (strings)
        match_type: Optional match type classification (VCT, VCL, OFFSEASON, SHOWMATCH).
                   If None, will be auto-detected.
    """
    conn = get_conn()
    ensure_matches_columns(conn)
    for item in ids_or_urls:
        match_row, maps_info, players_info = await scrape_match(item)
        
        if not match_type:
            match_name = match_row[4] if len(match_row) > 4 else ''
            tournament = match_row[1] if len(match_row) > 1 else ''
            if _detect_showmatch(match_name, tournament):
                match_type = 'SHOWMATCH'
            else:
                # Determine based on tournament name
                tournament_lower = (tournament or '').lower()
                if 'vct' in tournament_lower or 'champions tour' in tournament_lower or 'valorant champions tour' in tournament_lower:
                    match_type = 'VCT'
                elif 'vcl' in tournament_lower or 'challengers' in tournament_lower:
                    match_type = 'VCL'
                elif 'offseason' in tournament_lower:
                    match_type = 'OFFSEASON'
                else:
                    # Default to VCT for VCT pages (since we're scraping from vct-2024/vct-2025)
                    match_type = 'VCT'
        
        match_row_list = list(match_row)
        match_row_list[3] = match_type
        match_row = tuple(match_row_list)
        
        upsert_match(conn, match_row)
        m_lookup = upsert_maps(conn, maps_info)
        upsert_player_stats(conn, players_info, m_lookup)
        conn.commit()
    conn.close()


def ingest(ids_or_urls: list[str | int], match_type: str | None = None) -> None:
    """
    Synchronous wrapper for ingest_matches.
    
    Args:
        ids_or_urls: List of match IDs (integers) or URLs (strings)
        match_type: Optional match type classification (VCT, VCL, OFFSEASON, SHOWMATCH)
    """
    asyncio.run(ingest_matches(ids_or_urls, match_type))
