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


def _validate_match_data(match_row: tuple, maps_info: list, players_info: list) -> tuple[bool, list[str]]:
    """
    Validate extracted match data for consistency and completeness.
    
    Args:
        match_row: Tuple with match metadata
        maps_info: List of map tuples
        players_info: List of player stat tuples
    
    Returns:
        Tuple of (is_valid, list_of_warnings)
    """
    warnings = []
    is_valid = True
    
    # Validate match_id
    if not match_row[0] or match_row[0] <= 0:
        warnings.append("Invalid match_id")
        is_valid = False
    
    # Validate team names
    team_a, team_b = match_row[5], match_row[6]
    if not team_a or team_a == 'Unknown' or not team_b or team_b == 'Unknown':
        warnings.append("Missing or unknown team names")
    
    # Validate scores are reasonable
    a_score, b_score = match_row[7], match_row[8]
    if a_score is not None and b_score is not None:
        # Allow up to 5 for BO5 matches, no upper limit for series scores
        if a_score < 0 or b_score < 0:
            warnings.append(f"Unusual match scores: {a_score}-{b_score}")
    if a_score == b_score and a_score > 0:
        warnings.append(f"Match appears to be a draw: {a_score}-{b_score}")
    
    # Validate maps
    if not maps_info:
        warnings.append("No maps found for match")
    else:
        for map_info in maps_info:
            _, _, map_name, ta_score, tb_score = map_info
            if not map_name or map_name == 'Unknown':
                warnings.append("Map with unknown name found")
            if ta_score is not None and tb_score is not None:
                # Valid map scores: winner has >= 13 (game rule), no upper limit
                total = ta_score + tb_score
                max_score = max(ta_score, tb_score)
                min_score = min(ta_score, tb_score)
                
                # Check for invalid scores (only basic validation - trust the scraped data)
                if ta_score < 0 or tb_score < 0 or max_score < 13 or total < 13:
                    warnings.append(f"Unusual map scores: {map_name} {ta_score}-{tb_score}")
                # Check for draws (but allow 13-13 which can happen in overtime)
                elif ta_score == tb_score and ta_score > 0 and ta_score < 13:
                    warnings.append(f"Map appears to be a draw: {map_name} {ta_score}-{tb_score}")
    
    # Validate player stats
    if not players_info:
        warnings.append("No player stats found for match")
    else:
        # Check for reasonable stat values
        for player_info in players_info:
            _, _, player, team, agent, rating, acs, kills, deaths, assists = player_info
            if not player or player == 'Unknown':
                warnings.append("Player with unknown name found")
            if rating < 0 or rating > 5:
                warnings.append(f"Unusual rating for {player}: {rating}")
            if acs < 0 or acs > 500:
                warnings.append(f"Unusual ACS for {player}: {acs}")
    
    return is_valid, warnings


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


async def scrape_match(match_id_or_url: str | int) -> tuple[tuple, list[tuple], list[tuple], bool]:
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

    # Extract team names with multiple fallback strategies
    teams = soup.select('.match-header-link-name .wf-title-med')
    if len(teams) < 2:
        # Fallback: try alternative selectors
        teams = soup.select('.match-header-link-name .text-of, .match-header-link-name a')
    if len(teams) < 2:
        # Fallback: try header text parsing
        header_text = soup.select_one('.match-header-vs')
        if header_text:
            # Try to extract team names from header
            team_links = header_text.select('a')
            if len(team_links) >= 2:
                teams = team_links
    
    team_a = teams[0].get_text(strip=True) if len(teams) > 0 else 'Unknown'
    team_b = teams[1].get_text(strip=True) if len(teams) > 1 else 'Unknown'
    
    # Clean team names
    team_a = team_a.strip() if team_a else 'Unknown'
    team_b = team_b.strip() if team_b else 'Unknown'

    # Extract match-level scores with multiple strategies
    a_score = b_score = 0
    
    # Strategy 1: Extract from score spans (most reliable)
    score_spans = soup.select('.match-header-vs-score .js-spoiler span, .match-header-vs-score span, .match-header-vs .score, .match-header-vs-score')
    score_values = []
    for span in score_spans:
        text = span.get_text(strip=True)
        # Skip colon/spacer elements and non-numeric text
        if text and text not in [':', '-', 'vs', 'vs.', 'VS', 'VS.', '–', '—']:
            # Try to extract numbers from text
            numbers = re.findall(r'\d+', text)
            for num_str in numbers:
                try:
                    num = int(num_str)
                    # Valid match scores (0-5 for best-of-5, but allow up to 7 for safety)
                    if 0 <= num <= 7:
                        score_values.append(num)
                except ValueError:
                    pass
    
    # Also check the entire score container for patterns like "final3:1"
    score_container = soup.select_one('.match-header-vs-score, .match-header-vs')
    if score_container:
        container_text = score_container.get_text(' ', strip=True)
        # Look for patterns like "final3:1", "3:1", "final 3-1", etc.
        final_score_match = re.search(r'(?:final|result|score)[\s:]*(\d+)[:\-–—](\d+)', container_text, re.I)
        if final_score_match:
            score1, score2 = int(final_score_match.group(1)), int(final_score_match.group(2))
            # Allow up to 5 for BO5 matches (3-2 is max), but be lenient
            if score1 >= 0 and score2 >= 0 and score1 <= 10 and score2 <= 10:
                score_values.extend([score1, score2])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_scores = []
    for score in score_values:
        if score not in seen:
            seen.add(score)
            unique_scores.append(score)
    
    if len(unique_scores) >= 2:
        a_score, b_score = unique_scores[0], unique_scores[1]
    elif len(unique_scores) == 1:
        a_score = unique_scores[0]
    
    # Strategy 2: Extract from score container text (including patterns like "final2:0")
    if a_score == 0 and b_score == 0:
        score_container = soup.select_one('.match-header-vs-score, .match-header-vs, .match-header')
        if score_container:
            score_text = score_container.get_text(' ', strip=True)
            # Look for pattern like "2:0", "2 - 0", "2–0", or "final2:0" (no spaces)
            # Try with spaces first
            score_match = re.search(r'(\d+)\s*[:\-–—]\s*(\d+)', score_text)
            if not score_match:
                # Try without spaces (e.g., "final2:0", "2:0vs")
                score_match = re.search(r'(\d+)[:\-–—](\d+)', score_text)
            if score_match:
                try:
                    score1, score2 = int(score_match.group(1)), int(score_match.group(2))
                    # Allow up to 5 for BO5 matches, but be lenient
                    if score1 >= 0 and score2 >= 0 and score1 <= 10 and score2 <= 10:
                        a_score, b_score = score1, score2
                except ValueError:
                    pass
    
    # Strategy 3: Look for score in match result text
    if a_score == 0 and b_score == 0:
        result_elem = soup.select_one('.match-result, .result, [class*="result"]')
        if result_elem:
            result_text = result_elem.get_text(' ', strip=True)
            score_match = re.search(r'(\d+)\s*[:\-–—]\s*(\d+)', result_text)
            if score_match:
                try:
                    score1, score2 = int(score_match.group(1)), int(score_match.group(2))
                    # Allow up to 5 for BO5 matches, but be lenient
                    if score1 >= 0 and score2 >= 0 and score1 <= 10 and score2 <= 10:
                        a_score, b_score = score1, score2
                except ValueError:
                    pass

    # Check if this is a showmatch (from match-header-event-series element)
    is_showmatch = False
    showmatch_elem = soup.select_one('.match-header-event-series, [class*="event-series"]')
    if showmatch_elem:
        series_text = showmatch_elem.get_text(' ', strip=True).lower()
        if 'showmatch' in series_text:
            is_showmatch = True
    
    # Extract tournament and match info with multiple fallbacks
    match_name_elem = soup.select_one('.match-header-event, .match-header .event, [class*="event"]')
    match_name = ''
    if match_name_elem:
        match_name = match_name_elem.get_text(' ', strip=True)
    
    # Fallback: try to get from page title or other elements
    if not match_name or len(match_name) < 5:
        title_elem = soup.find('title')
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            # Extract from title like "Team A vs Team B - Tournament Name | VLR.gg"
            if ' - ' in title_text:
                parts = title_text.split(' - ', 1)
                if len(parts) > 1:
                    match_name = parts[1].split(' | ')[0].strip()
            elif ' | ' in title_text:
                match_name = title_text.split(' | ')[0].strip()
            else:
                match_name = title_text.strip()
    
    # Additional fallback: try breadcrumbs or navigation
    if not match_name or len(match_name) < 5:
        breadcrumb = soup.select_one('.breadcrumb, .wf-breadcrumb, nav[aria-label="Breadcrumb"], [class*="breadcrumb"]')
        if breadcrumb:
            breadcrumb_text = breadcrumb.get_text(' ', strip=True)
            # Extract tournament name from breadcrumb
            parts = breadcrumb_text.split('>') if '>' in breadcrumb_text else breadcrumb_text.split('/')
            for part in reversed(parts):
                part = part.strip()
                if part and len(part) > 5 and not part.lower() in ['home', 'matches', 'events', 'vlr.gg']:
                    match_name = part
                    break
    
    # Final fallback: use URL slug
    if not match_name or len(match_name) < 5:
        url_parts = url.split('/')
        if len(url_parts) > 1:
            slug = url_parts[-1] if url_parts[-1] else url_parts[-2]
            match_name = slug.replace('-', ' ').title() if slug else 'Unknown Match'
    
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
        
        # Strategy 1: Extract final scores from the exact VLR.gg structure
        # Structure: .vm-stats-game-header > .team (left) and .team.mod-right (right)
        # Each team div contains a .score div with the final map score
        # Example: <div class="team"><div class="score mod-win">20</div></div>
        #          <div class="team mod-right"><div class="score">18</div></div>
        score_elems = []
        if header:
            # Direct CSS selector approach: find .team containers, then .score within them
            # This matches the exact HTML structure: .vm-stats-game-header > .team > .score
            team_containers = header.select('div.team, div[class*="team"]')
            
            for team_container in team_containers:
                # Skip team-name divs
                classes = team_container.get('class', [])
                if classes:
                    class_str = ' '.join(classes) if isinstance(classes, list) else str(classes)
                    if 'team-name' in class_str.lower():
                        continue
                
                # Find score div within this team container
                score_elem = team_container.select_one('div.score, div[class*="score"]')
                if score_elem:
                    score_elems.append(score_elem)
            
            # Fallback: direct selector if team-based approach didn't work
            if not score_elems:
                score_elems = header.select('div.score, div[class*="score"]')
        
        # Extract scores from found elements
        # Structure: .vm-stats-game-header > .team (left) and .team.mod-right (right)
        # Each team contains a .score div with the final score
        if score_elems:
            # Extract all scores with their team positions
            scores = []
            for score_elem in score_elems:
                score_text = score_elem.get_text(strip=True)
                try:
                    score_num = int(score_text)
                    # Accept all non-negative scores (no upper limit - games can go 50+ rounds in overtime)
                    if score_num >= 0:
                        # Find parent team container to determine left/right
                        parent = score_elem.parent
                        is_right = False
                        for _ in range(5):
                            if parent and parent.name == 'div':
                                parent_classes = parent.get('class', [])
                                if parent_classes:
                                    parent_class_str = ' '.join(parent_classes) if isinstance(parent_classes, list) else str(parent_classes)
                                    if 'team' in parent_class_str.lower():
                                        is_right = 'right' in parent_class_str.lower() or 'mod-right' in parent_class_str.lower()
                                        break
                            parent = getattr(parent, 'parent', None)
                            if not parent:
                                break
                        scores.append((score_num, is_right, score_elem))
                except ValueError:
                    pass
            
            # We found scores from within the header, so they should be valid
            # We want exactly 2 scores, one for each team
            # Sort by position (left first, right second) and assign
            if len(scores) >= 2:
                # Sort by position (left first, right second)
                scores.sort(key=lambda x: x[1])  # False (left) before True (right)
                a_map_score, b_map_score = scores[0][0], scores[1][0]
            elif len(scores) == 1:
                # Only one score found - assign to appropriate team
                score_num, is_right, _ = scores[0]
                if is_right:
                    b_map_score = score_num
                else:
                    a_map_score = score_num
        
        # Only use fallback strategies if we didn't find scores from the exact structure
        # Try to match scores to teams by position/context
        if (a_map_score is None or b_map_score is None) and header:
            header_html = str(header)
            # Look for team names in header to determine score order
            header_lower = header_html.lower()
            team_a_lower = team_a.lower() if team_a else ''
            team_b_lower = team_b.lower() if team_b else ''
            
            # Find team positions in header
            team_a_pos = header_lower.find(team_a_lower) if team_a_lower else -1
            team_b_pos = header_lower.find(team_b_lower) if team_b_lower else -1
            
            # Extract all numbers from header
            header_text = header.get_text(' ', strip=True)
            # Strip out time-like fragments
            header_clean = re.sub(r'\d+:\d{2}:\d{2}', ' ', header_text)
            header_clean = re.sub(r'\d+:\d{2}(?!\d)', ' ', header_clean)
            
            # Try to find score pattern with team context
            # Pattern: "13 TeamA ... TeamB ... 8" or "TeamA 13 ... TeamB 8"
            score_match = re.search(r'(\d{1,2})\s*[:\-–—]\s*(\d{1,2})', header_clean)
            if score_match:
                score1, score2 = int(score_match.group(1)), int(score_match.group(2))
                # Accept any non-negative scores, but validate at least one >= 13 (game rule)
                if score1 >= 0 and score2 >= 0 and (score1 >= 13 or score2 >= 13):
                    # Try to determine which score belongs to which team by proximity
                    score1_str = score_match.group(1)
                    score2_str = score_match.group(2)
                    score1_pos = header_text.find(score1_str)
                    score2_pos = header_text.find(score2_str)
                    
                    # Find which team name is closer to which score
                    if team_a_pos >= 0 and team_b_pos >= 0:
                        # Calculate distances
                        dist_a_to_s1 = abs(team_a_pos - score1_pos) if score1_pos >= 0 else float('inf')
                        dist_a_to_s2 = abs(team_a_pos - score2_pos) if score2_pos >= 0 else float('inf')
                        dist_b_to_s1 = abs(team_b_pos - score1_pos) if score1_pos >= 0 else float('inf')
                        dist_b_to_s2 = abs(team_b_pos - score2_pos) if score2_pos >= 0 else float('inf')
                        
                        # Assign scores to closest teams
                        if dist_a_to_s1 < dist_b_to_s1 and dist_b_to_s2 < dist_a_to_s2:
                            # Score1 is closer to team A, score2 to team B
                            a_map_score, b_map_score = score1, score2
                        elif dist_b_to_s1 < dist_a_to_s1 and dist_a_to_s2 < dist_b_to_s2:
                            # Score1 is closer to team B, score2 to team A
                            a_map_score, b_map_score = score2, score1
                        elif team_a_pos < team_b_pos:
                            # Teams are in order, assume scores are in same order
                            a_map_score, b_map_score = score1, score2
                        else:
                            # Teams are reversed, assume scores are reversed
                            a_map_score, b_map_score = score2, score1
                    elif team_a_pos >= 0:
                        # Only found team A - check which score is closer
                        if abs(team_a_pos - score1_pos) < abs(team_a_pos - score2_pos):
                            a_map_score, b_map_score = score1, score2
                        else:
                            a_map_score, b_map_score = score2, score1
                    elif team_b_pos >= 0:
                        # Only found team B - check which score is closer
                        if abs(team_b_pos - score1_pos) < abs(team_b_pos - score2_pos):
                            a_map_score, b_map_score = score2, score1
                        else:
                            a_map_score, b_map_score = score1, score2
                    else:
                        # No team names found - default to first score is team A
                        a_map_score, b_map_score = score1, score2
            
            # Strategy 2: Fallback - look for score elements directly in header
            if a_map_score is None or b_map_score is None:
                # Try finding score elements directly
                score_elems = header.select('.score, [class*="score"]')
                score_numbers = []
                for score_elem in score_elems:
                    score_text = score_elem.get_text(strip=True)
                    try:
                        score_num = int(score_text)
                        if score_num >= 13:  # Only require winner >= 13, no upper limit
                            # Check if this is a final score (not part of time or other data)
                            parent_text = (score_elem.find_parent().get_text(' ', strip=True) if score_elem.find_parent() else '').lower()
                            # Skip if it's clearly part of time or other non-score element
                            if ':' not in parent_text[:30] and 'time' not in parent_text[:30]:
                                score_numbers.append(score_num)
                    except ValueError:
                        pass
                
                # Remove duplicates and use the scores
                if len(score_numbers) >= 2:
                    unique_scores = []
                    seen = set()
                    for s in score_numbers:
                        if s not in seen:
                            seen.add(s)
                            unique_scores.append(s)
                    
                    if len(unique_scores) >= 2:
                        # Try to determine order based on element positions
                        first_elem = None
                        second_elem = None
                        for score_elem in score_elems:
                            score_text = score_elem.get_text(strip=True)
                            try:
                                if int(score_text) == unique_scores[0] and first_elem is None:
                                    first_elem = score_elem
                                elif int(score_text) == unique_scores[1] and second_elem is None:
                                    second_elem = score_elem
                            except ValueError:
                                pass
                        
                        if first_elem and second_elem:
                            # Check which is left/right based on classes or position
                            first_classes = ' '.join(first_elem.get('class', []))
                            second_classes = ' '.join(second_elem.get('class', []))
                            
                            # Check parent team containers
                            first_parent = first_elem.find_parent(class_=re.compile('team'))
                            second_parent = second_elem.find_parent(class_=re.compile('team'))
                            
                            if first_parent and second_parent:
                                first_team_classes = ' '.join(first_parent.get('class', []))
                                second_team_classes = ' '.join(second_parent.get('class', []))
                                
                                # Determine order
                                if 'right' in first_team_classes or 'mod-right' in first_team_classes:
                                    a_map_score, b_map_score = unique_scores[1], unique_scores[0]
                                elif 'right' in second_team_classes or 'mod-right' in second_team_classes:
                                    a_map_score, b_map_score = unique_scores[0], unique_scores[1]
                                else:
                                    # Default: first is left team
                                    a_map_score, b_map_score = unique_scores[0], unique_scores[1]
                            else:
                                # Default order
                                a_map_score, b_map_score = unique_scores[0], unique_scores[1]
                        else:
                            # Just use the scores in order
                            a_map_score, b_map_score = unique_scores[0], unique_scores[1]
            
            # Strategy 2: Direct text extraction - look for large numbers (13-20) near team names
            # This is a more aggressive approach for cases where structured extraction fails
            if a_map_score is None or b_map_score is None:
                header_text = header.get_text(' ', strip=True)
                # Find all numbers 13-20 in the header (these are likely final map scores, not round scores)
                large_numbers = []
                for match in re.finditer(r'\b(1[3-9]|20)\b', header_text):
                    num = int(match.group(1))
                    pos = match.start()
                    # Check context around this number
                    context_start = max(0, pos - 100)
                    context_end = min(len(header_text), pos + 100)
                    context = header_text[context_start:context_end].lower()
                    
                    # Check if this number appears near team names (more likely to be a final score)
                    has_team_a = team_a_lower in context if team_a_lower else False
                    has_team_b = team_b_lower in context if team_b_lower else False
                    
                    if has_team_a or has_team_b:
                        # Determine which team this score likely belongs to
                        is_right = False
                        if has_team_b:
                            team_b_pos_in_context = context.find(team_b_lower)
                            team_a_pos_in_context = context.find(team_a_lower) if has_team_a else -1
                            # If team B appears before team A, or team A not found, this is likely team B's score
                            if team_a_pos_in_context == -1 or (team_b_pos_in_context >= 0 and team_b_pos_in_context < team_a_pos_in_context):
                                is_right = True
                        large_numbers.append((num, pos, is_right))
                
                # If we found 2 large numbers, use them as scores
                if len(large_numbers) >= 2:
                    # Sort by position
                    large_numbers.sort(key=lambda x: x[1])
                    # Assign based on team positions
                    if large_numbers[0][2] != large_numbers[1][2]:
                        # Different teams
                        if large_numbers[0][2]:  # First is right
                            a_map_score, b_map_score = large_numbers[1][0], large_numbers[0][0]
                        else:  # First is left
                            a_map_score, b_map_score = large_numbers[0][0], large_numbers[1][0]
                    else:
                        # Same team or unclear - use in order (first is left, second is right)
                        a_map_score, b_map_score = large_numbers[0][0], large_numbers[1][0]
            
            # Strategy 3: Look for scores near team names (original fallback)
            if a_map_score is None or b_map_score is None:
                # Find all numbers that could be map scores
                # No upper limit - games can go 50+ rounds in infinite overtime
                numbers = []
                for match in re.finditer(r'\b(\d{1,3})\b', header_text):  # Allow up to 3 digits (e.g., 100+)
                    num = int(match.group(1))
                    # Accept any non-negative number (no upper limit)
                    if num >= 0:
                        numbers.append((num, match.start()))
                
                if len(numbers) >= 2:
                    # Filter to find valid map score pairs (at least one >= 13, no upper limit)
                    valid_pairs = []
                    for i, (num1, pos1) in enumerate(numbers):
                        for j, (num2, pos2) in enumerate(numbers[i+1:], i+1):
                            # Valid map score: at least one team has >= 13 (game rule), total >= 13, no upper limit
                            if (num1 >= 13 or num2 >= 13) and (num1 + num2) >= 13:
                                valid_pairs.append((num1, num2, pos1, pos2))
                    
                    if valid_pairs:
                        # Use the pair that's most likely (first/last numbers, or closest to team names)
                        if team_a_pos >= 0 and team_b_pos >= 0:
                            # Find pair closest to team positions
                            best_pair = None
                            best_score = float('inf')
                            for num1, num2, pos1, pos2 in valid_pairs:
                                # Calculate distance to teams
                                dist = abs(pos1 - team_a_pos) + abs(pos2 - team_b_pos)
                                if dist < best_score:
                                    best_score = dist
                                    best_pair = (num1, num2, pos1, pos2)
                            
                            if best_pair:
                                num1, num2, pos1, pos2 = best_pair
                                # Determine which score belongs to which team
                                if abs(pos1 - team_a_pos) < abs(pos2 - team_a_pos):
                                    a_map_score, b_map_score = num1, num2
                                else:
                                    a_map_score, b_map_score = num2, num1
                        else:
                            # Use first valid pair (usually first and last numbers)
                            num1, num2, _, _ = valid_pairs[0]
                            a_map_score, b_map_score = num1, num2
                    else:
                        # No valid pairs found, try first and last numbers anyway
                        score1, pos1 = numbers[0]
                        score2, pos2 = numbers[-1]
                        # If at least one is >= 13, use them
                        if score1 >= 13 or score2 >= 13:
                            if team_a_pos >= 0 and team_b_pos >= 0:
                                if abs(pos1 - team_a_pos) < abs(pos2 - team_a_pos):
                                    a_map_score, b_map_score = score1, score2
                                else:
                                    a_map_score, b_map_score = score2, score1
                            else:
                                a_map_score, b_map_score = score1, score2
        
        # Strategy 3: Look for final score in large/prominent number elements
        # These are typically the final map scores, not intermediate scores like 12-12
        if (a_map_score is None or b_map_score is None):
            # Look for large number elements that represent final scores
            # These are often in specific positions or have specific styling
            large_numbers = []
            
            # Check header for large number elements
            if header:
                # Look for elements with large numbers (13-20) that are likely final scores
                for elem in header.find_all(['div', 'span', 'td', 'th']):
                    text = elem.get_text(strip=True)
                    # Check if this is a large number (final score)
                    if re.match(r'^(1[3-9]|20)$', text):
                        try:
                            num = int(text)
                            # Get element's position and styling info
                            classes = ' '.join(elem.get('class', []))
                            # Prioritize elements that look like final scores
                            # (not intermediate scores, not in time displays, etc.)
                            parent_text = (elem.find_parent().get_text(' ', strip=True) if elem.find_parent() else '').lower()
                            # Skip if it's clearly part of a time or other non-score element
                            if ':' not in parent_text[:20] and 'time' not in classes.lower():
                                large_numbers.append((num, elem, text))
                        except ValueError:
                            pass
            
            # If we found large numbers, try to pair them as final scores
            if len(large_numbers) >= 2:
                # Get the numbers
                nums = [n[0] for n in large_numbers]
                # Look for a pair where at least one is >= 13 and they're valid map scores
                for i, (num1, elem1, text1) in enumerate(large_numbers):
                    for j, (num2, elem2, text2) in enumerate(large_numbers[i+1:], i+1):
                        if (num1 >= 13 or num2 >= 13) and (num1 + num2) >= 13 and (num1 + num2) <= 30:
                            # Check element positions to determine team assignment
                            # Elements closer to team names are more likely to be that team's score
                            if header:
                                header_text = header.get_text(' ', strip=True)
                                pos1 = header_text.find(text1)
                                pos2 = header_text.find(text2)
                                
                                if team_a_pos >= 0 and team_b_pos >= 0:
                                    # Assign based on proximity to team names
                                    if abs(pos1 - team_a_pos) < abs(pos2 - team_a_pos):
                                        a_map_score, b_map_score = num1, num2
                                    else:
                                        a_map_score, b_map_score = num2, num1
                                else:
                                    # Use first and second
                                    a_map_score, b_map_score = num1, num2
                                break
                    if a_map_score is not None:
                        break
        
        # Strategy 4: Look for score in table headers or summary
        if (a_map_score is None or b_map_score is None):
            # Check if there's a score summary in the game div
            summary = game_div.select_one('.vm-stats-game-summary, .map-summary')
            if summary:
                summary_text = summary.get_text(' ', strip=True)
                score_match = re.search(r'(\d{1,2})\s*[:\-–—]\s*(\d{1,2})', summary_text)
                if score_match:
                    score1, score2 = int(score_match.group(1)), int(score_match.group(2))
                    # Allow 0-20, validate at least one >= 13
                    if score1 >= 0 and score2 >= 0 and (score1 >= 13 or score2 >= 13):
                        a_map_score, b_map_score = score1, score2

        # Validate map scores - filter out invalid scores
        # Valid Valorant map scores: winner has >= 13, loser has 0-12 (or higher in overtime)
        # IMPORTANT: 12-12 is an intermediate score during overtime, not the final score
        # Final scores in overtime will be higher (e.g., 15-17, 14-16, etc.)
        if a_map_score is not None and b_map_score is not None:
            # Check if scores look like valid map scores
            total = a_map_score + b_map_score
            max_score = max(a_map_score, b_map_score)
            min_score = min(a_map_score, b_map_score)
            
            # Minimal validation: only require winner >= 13 (game rule)
            # No upper limits - games can go to 50+ rounds in infinite overtime
            # Only filter out clearly invalid scores:
            # - Winner must have >= 13 (game rule)
            # - Total must be >= 13 (minimum for a completed map)
            # - No negative scores
            if max_score < 13 or total < 13 or a_map_score < 0 or b_map_score < 0:
                # These are likely invalid - set to None
                a_map_score, b_map_score = None, None
            elif max_score == min_score and max_score < 13:
                # Draw with low scores (like 4-4, 6-6) - invalid (but allow 13-13+ which can happen)
                a_map_score, b_map_score = None, None
        
        # Always insert map, even if scores are missing (for consistency)
        # This allows player stats to be inserted even if map scores aren't available
        maps_info.append((mid, game_id, map_name, a_map_score, b_map_score))
        
        # Only process player stats if we have a valid game_div with table
        if not game_div.select('table.wf-table-inset tbody tr'):
            continue
        for row in game_div.select('table.wf-table-inset tbody tr'):
            cells = row.find_all('td')
            if len(cells) < 7:
                continue
            
            # Extract player name with multiple fallback strategies
            player_cell = cells[0]
            player = None
            team = None
            
            if player_cell:
                # Try primary selector
                player_elem = player_cell.find('div', class_='text-of')
                if player_elem:
                    player = player_elem.get_text(strip=True)
                else:
                    # Fallback: try other common selectors
                    player_elem = player_cell.find('a') or player_cell.find('span', class_='text-of')
                    if player_elem:
                        player = player_elem.get_text(strip=True)
                    else:
                        # Last resort: get text from cell directly
                        player = player_cell.get_text(strip=True).split('\n')[0].strip()
                
                # Extract team name
                team_elem = player_cell.find('div', class_='ge-text-light')
                if team_elem:
                    team = team_elem.get_text(strip=True)
                else:
                    # Fallback: try other selectors
                    team_elem = player_cell.find('span', class_='ge-text-light') or player_cell.find('div', class_='text-of')
                    if team_elem and team_elem != player_elem:
                        team = team_elem.get_text(strip=True)
                    else:
                        # Try to extract from cell text (team usually appears after player name)
                        cell_text = player_cell.get_text('\n', strip=True)
                        lines = [l.strip() for l in cell_text.split('\n') if l.strip()]
                        if len(lines) > 1:
                            team = lines[1]
            
            # Extract agent from image
            img = row.find('img')
            agent = None
            if img:
                agent = img.get('title') or img.get('alt') or img.get('data-title')
                if not agent:
                    # Try to get from parent or nearby elements
                    img_parent = img.parent
                    if img_parent:
                        agent = img_parent.get('title') or img_parent.get_text(strip=True)

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

    # Check if match is incomplete/live
    is_live = False
    is_upcoming = False
    status_indicators = soup.select('.match-header-status, .match-status, [class*="status"], [class*="live"], [class*="upcoming"]')
    for indicator in status_indicators:
        text = indicator.get_text(strip=True).lower()
        if 'live' in text or 'in progress' in text or 'playing' in text:
            is_live = True
        if 'upcoming' in text or 'scheduled' in text or 'tbd' in text:
            is_upcoming = True
    
    # Check page for live/upcoming indicators in text
    page_text = soup.get_text().lower()
    if 'live' in page_text or 'in progress' in page_text:
        is_live = True
    if 'upcoming' in page_text or 'scheduled' in page_text:
        is_upcoming = True
    
    # Calculate match scores from map wins - this is the most reliable source
    # Count maps where team_a won (ta_score > tb_score)
    a_w = sum(1 for _, _, _, tas, tbs in maps_info 
              if tas is not None and tbs is not None and tas > tbs)
    # Count maps where team_b won (tb_score > ta_score)
    b_w = sum(1 for _, _, _, tas, tbs in maps_info 
              if tas is not None and tbs is not None and tbs > tas)
    
    # Count total maps with valid scores
    total_maps_with_scores = len([m for m in maps_info if m[3] is not None and m[4] is not None])
    
    # Check if header indicates a completed match (e.g., "final", "result")
    header_indicates_complete = False
    score_container = soup.select_one('.match-header-vs-score, .match-header-vs')
    if score_container:
        container_text = score_container.get_text(' ', strip=True).lower()
        if 'final' in container_text or 'result' in container_text or 'complete' in container_text:
            header_indicates_complete = True
    
    # Decide which score to use:
    # - If header shows "final X-Y" and we have a conflict, trust the header (it's the official result)
    # - Otherwise, prefer map wins as they're more reliable
    header_score_extracted = (a_score > 0 or b_score > 0) and not (a_score == 0 and b_score == 0)
    
    if header_indicates_complete and header_score_extracted:
        # Header shows completed match with score - trust it
        # But verify it makes sense (not a draw, winner has >= 2 maps)
        if a_score != b_score and max(a_score, b_score) >= 2:
            # Header score is valid - use it
            pass  # Keep a_score, b_score from header
        elif a_w + b_w > 0:
            # Header score is invalid, use map wins
            a_score, b_score = a_w, b_w
    elif a_w + b_w > 0:
        # No header completion indicator, prefer map wins
        a_score, b_score = a_w, b_w
    elif a_score == 0 and b_score == 0:
        # No scores extracted and no map wins - might be upcoming match
        # Keep scores as 0-0
        pass
    # Otherwise, keep the extracted scores (they might be correct if maps are missing)
    
    # Final validation and fix: if we have a draw, try to find the actual winner
    if a_score == b_score and a_score > 0:
        # This shouldn't happen in VCT - matches don't end in draws
        # If match is live/upcoming, that's expected - but if it's completed, we have a problem
        
        if is_live or is_upcoming:
            # Match is still in progress, draw is expected
            # But we shouldn't be scraping incomplete matches - set to 0-0
            a_score, b_score = 0, 0
        elif total_maps_with_scores >= 2:
            # We have at least 2 maps with scores, so a draw is impossible
            # Try to find the actual winner by checking:
            # 1. Look for a third map that might have been missed
            # 2. Check if map scores are wrong (maybe team order is swapped)
            # 3. Look for final score in other parts of the page
            
            # Strategy 1: Check if there are more game divs than maps we parsed
            all_game_divs = soup.select('div.vm-stats-game[data-game-id]')
            game_ids_found = set()
            for div in all_game_divs:
                gid = div.get('data-game-id')
                if gid and gid != 'all':
                    game_ids_found.add(gid)
            
            # Also check map navigation for all available maps
            map_nav_items = soup.select('.vm-stats-gamesnav-item, .vm-stats-gamesnav a, [class*="gamesnav"] a')
            for nav_item in map_nav_items:
                gid_attr = nav_item.get('data-game-id')
                if not gid_attr:
                    # Try to extract from href
                    href = nav_item.get('href', '')
                    if 'game-id' in href or 'game' in href.lower():
                        # Try to extract ID from href
                        gid_match = re.search(r'game[_-]?id[=:](\w+)', href, re.I)
                        if gid_match:
                            gid_attr = gid_match.group(1)
                if gid_attr:
                    game_ids_found.add(str(gid_attr))
            
            # Check if we're missing any maps
            maps_found = set(m[1] for m in maps_info)
            missing_maps = game_ids_found - maps_found
            
            # Special case: if we have 2-2, we MUST have a 5th map (best-of-5)
            if a_score == 2 and b_score == 2 and len(missing_maps) == 0:
                # Look for 5th map more aggressively - check all divs
                all_divs = soup.find_all('div', attrs={'data-game-id': True})
                for div in all_divs:
                    gid = div.get('data-game-id')
                    if gid and gid != 'all' and gid not in maps_found:
                        missing_maps.add(gid)
            
            if missing_maps:
                # We missed some maps - try to parse them
                for missing_gid in missing_maps:
                    missing_div = soup.select_one(f'div.vm-stats-game[data-game-id="{missing_gid}"]')
                    if missing_div:
                        # Try to extract map info from this div
                        header = missing_div.find('div', class_='vm-stats-game-header')
                        if header:
                            # Extract map name and scores
                            map_name_elem = header.find(class_='map')
                            map_name = map_name_elem.get_text(strip=True) if map_name_elem else 'Unknown'
                            map_name = _clean_map_name(map_name)
                            
                            # Try to extract scores
                            header_text = header.get_text(' ', strip=True)
                            score_match = re.search(r'(\d{1,2})\s*[:\-–—]\s*(\d{1,2})', header_text)
                            if score_match:
                                ta_map, tb_map = int(score_match.group(1)), int(score_match.group(2))
                                # Validate: must have at least one team with >= 13 (game rule), no upper limit
                                total = ta_map + tb_map
                                max_score = max(ta_map, tb_map)
                                if max_score >= 13 and total >= 13:
                                    maps_info.append((mid, missing_gid, map_name, ta_map, tb_map))
                                    if ta_map > tb_map:
                                        a_w += 1
                                    elif tb_map > ta_map:
                                        b_w += 1
            
            # Recalculate scores after finding missing maps
            if a_w + b_w > a_score + b_score:
                a_score, b_score = a_w, b_w
            
            # Strategy 2: Try to find winner from page title or metadata
            if a_score == b_score:
                title = soup.find('title')
                if title:
                    title_text = title.get_text()
                    # Look for score in title like "Team A 2-1 Team B"
                    title_score = re.search(rf'{re.escape(team_a)}\s+(\d+)[:\-–—](\d+)\s+{re.escape(team_b)}', title_text, re.I)
                    if not title_score:
                        title_score = re.search(rf'{re.escape(team_b)}\s+(\d+)[:\-–—](\d+)\s+{re.escape(team_a)}', title_text, re.I)
                    if title_score:
                        score1, score2 = int(title_score.group(1)), int(title_score.group(2))
                        if score1 != score2 and max(score1, score2) >= 2:
                            # Found a valid final score in title
                            if team_a.lower() in title_text.lower() and title_text.lower().find(team_a.lower()) < title_text.lower().find(team_b.lower()):
                                a_score, b_score = score1, score2
                            else:
                                a_score, b_score = score2, score1
            
            # Strategy 3: Check map navigation for completed maps
            if a_score == b_score:
                map_nav = soup.select('.vm-stats-gamesnav-item')
                completed_maps = []
                for nav_item in map_nav:
                    nav_text = nav_item.get_text(strip=True)
                    # Look for score indicators in nav (some sites show scores in nav)
                    nav_score = re.search(r'(\d+)[:\-–—](\d+)', nav_text)
                    if nav_score:
                        s1, s2 = int(nav_score.group(1)), int(nav_score.group(2))
                        # Allow 0-20, validate at least one >= 13 for valid map score
                        if s1 != s2 and 0 <= s1 <= 20 and 0 <= s2 <= 20 and (s1 >= 13 or s2 >= 13):
                            completed_maps.append((s1, s2))
                
                # If we found completed maps in nav, count wins
                if completed_maps:
                    nav_a_wins = sum(1 for s1, s2 in completed_maps if s1 > s2)
                    nav_b_wins = sum(1 for s1, s2 in completed_maps if s2 > s1)
                    if nav_a_wins + nav_b_wins > 0 and nav_a_wins != nav_b_wins:
                        a_score, b_score = nav_a_wins, nav_b_wins
            
            # Strategy 4: If still a draw with 2 maps, try swapping team assignments
            # The issue might be that team_a and team_b are swapped on one or more maps
            if a_score == b_score and total_maps_with_scores == 2:
                # Try swapping scores on each map and see if that gives us a valid result
                for i, map_info in enumerate(maps_info):
                    if map_info[3] is not None and map_info[4] is not None:
                        # Try swapping this map's scores
                        test_maps = maps_info.copy()
                        test_maps[i] = (map_info[0], map_info[1], map_info[2], map_info[4], map_info[3])
                        
                        test_a_w = sum(1 for _, _, _, tas, tbs in test_maps 
                                      if tas is not None and tbs is not None and tas > tbs)
                        test_b_w = sum(1 for _, _, _, tas, tbs in test_maps 
                                      if tas is not None and tbs is not None and tbs > tas)
                        
                        if test_a_w != test_b_w and test_a_w + test_b_w == 2:
                            # Swapping this map fixes it!
                            maps_info[i] = test_maps[i]
                            a_score, b_score = test_a_w, test_b_w
                            break
            
            # Strategy 5: Check if we can determine winner from player stats
            # If one team has significantly better stats across all maps, they likely won
            if a_score == b_score and len(players_info) > 0:
                # Calculate average ACS per team
                team_a_stats = [p for p in players_info if p[3] == team_a]
                team_b_stats = [p for p in players_info if p[3] == team_b]
                
                if team_a_stats and team_b_stats:
                    avg_acs_a = sum(p[6] for p in team_a_stats) / len(team_a_stats) if team_a_stats else 0
                    avg_acs_b = sum(p[6] for p in team_b_stats) / len(team_b_stats) if team_b_stats else 0
                    
                    # If one team has significantly better stats, they likely won
                    # But this is unreliable, so only use as last resort
                    # Actually, don't use this - it's too unreliable
                    pass

    match_row = (
        mid, tournament, stage, '', match_name,
        team_a, team_b, a_score, b_score, f"{team_a} {a_score}-{b_score} {team_b}", dt_utc, date_str
    )
    return match_row, maps_info, players_info, is_showmatch


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


async def ingest_matches(ids_or_urls: list[str | int], match_type: str | None = None, validate: bool = True) -> None:
    """
    Ingest matches from vlr.gg into the database.
    
    Auto-detects match type (VCT/VCL/OFFSEASON/SHOWMATCH) if not provided by analyzing
    tournament name and match name for showmatch indicators.
    
    Args:
        ids_or_urls: List of match IDs (integers) or URLs (strings)
        match_type: Optional match type classification (VCT, VCL, OFFSEASON, SHOWMATCH).
                   If None, will be auto-detected.
        validate: If True, validate data before inserting (default: True)
    """
    conn = get_conn()
    ensure_matches_columns(conn)
    
    success_count = 0
    error_count = 0
    
    for item in ids_or_urls:
        try:
            match_row, maps_info, players_info, is_showmatch_from_html = await scrape_match(item)
            match_id = match_row[0]
            
            # Validate data if requested
            if validate:
                is_valid, warnings = _validate_match_data(match_row, maps_info, players_info)
                if warnings:
                    print(f"Match {match_id} warnings: {', '.join(warnings[:3])}")  # Show first 3 warnings
            
            # Auto-detect match type if not provided
            if not match_type:
                # Use HTML-based detection first (most reliable)
                if is_showmatch_from_html:
                    match_type = 'SHOWMATCH'
                else:
                    # Fallback to name-based detection
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
            
            # Insert data
            upsert_match(conn, match_row)
            m_lookup = upsert_maps(conn, maps_info)
            upsert_player_stats(conn, players_info, m_lookup)
            conn.commit()
            
            success_count += 1
            # Reset match_type for next iteration (it's per-match)
            match_type = None
            
        except Exception as e:
            error_count += 1
            print(f"Error ingesting match {item}: {e}")
            import traceback
            traceback.print_exc()
            # Continue with next match
            continue
    
    conn.close()
    
    if success_count > 0 or error_count > 0:
        print(f"Ingestion complete: {success_count} successful, {error_count} errors")


def ingest(ids_or_urls: list[str | int], match_type: str | None = None) -> None:
    """
    Synchronous wrapper for ingest_matches.
    
    Args:
        ids_or_urls: List of match IDs (integers) or URLs (strings)
        match_type: Optional match type classification (VCT, VCL, OFFSEASON, SHOWMATCH)
    """
    asyncio.run(ingest_matches(ids_or_urls, match_type))
