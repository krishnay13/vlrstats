"""
Match metadata extraction from VLR.gg.

Extracts match-level information:
- Teams and scores
- Tournament, stage, match name
- Date/time
- Match type detection
"""
import re
from datetime import datetime
from bs4 import BeautifulSoup
from typing import Optional, Tuple
from .base import fetch_html


def extract_match_datetime(soup: BeautifulSoup) -> Optional[str]:
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


def extract_teams(soup: BeautifulSoup) -> Tuple[str, str]:
    """
    Extract team names from match page.
    
    Args:
        soup: BeautifulSoup parsed HTML
    
    Returns:
        Tuple of (team_a, team_b)
    """
    teams = soup.select('.match-header-link-name .wf-title-med')
    if len(teams) < 2:
        teams = soup.select('.match-header-link-name .text-of, .match-header-link-name a')
    if len(teams) < 2:
        header_text = soup.select_one('.match-header-vs')
        if header_text:
            team_links = header_text.select('a')
            if len(team_links) >= 2:
                teams = team_links
    
    team_a = teams[0].get_text(strip=True) if len(teams) > 0 else 'Unknown'
    team_b = teams[1].get_text(strip=True) if len(teams) > 1 else 'Unknown'
    
    team_a = team_a.strip() if team_a else 'Unknown'
    team_b = team_b.strip() if team_b else 'Unknown'
    
    return team_a, team_b


def extract_match_scores(soup: BeautifulSoup) -> Tuple[int, int]:
    """
    Extract match-level scores from match page.
    
    Args:
        soup: BeautifulSoup parsed HTML
    
    Returns:
        Tuple of (team_a_score, team_b_score)
    """
    a_score = b_score = 0
    
    # Strategy 1: Extract from score spans
    score_spans = soup.select('.match-header-vs-score .js-spoiler span, .match-header-vs-score span, .match-header-vs .score, .match-header-vs-score')
    score_values = []
    for span in score_spans:
        text = span.get_text(strip=True)
        if text and text not in [':', '-', 'vs', 'vs.', 'VS', 'VS.', '–', '—']:
            numbers = re.findall(r'\d+', text)
            for num_str in numbers:
                try:
                    num = int(num_str)
                    if 0 <= num <= 7:
                        score_values.append(num)
                except ValueError:
                    pass
    
    # Check entire score container for patterns like "final3:1"
    score_container = soup.select_one('.match-header-vs-score, .match-header-vs')
    if score_container:
        container_text = score_container.get_text(' ', strip=True)
        final_score_match = re.search(r'(?:final|result|score)[\s:]*(\d+)[:\-–—](\d+)', container_text, re.I)
        if final_score_match:
            score1, score2 = int(final_score_match.group(1)), int(final_score_match.group(2))
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
    
    # Strategy 2: Extract from score container text
    if a_score == 0 and b_score == 0:
        score_container = soup.select_one('.match-header-vs-score, .match-header-vs, .match-header')
        if score_container:
            score_text = score_container.get_text(' ', strip=True)
            score_match = re.search(r'(\d+)\s*[:\-–—]\s*(\d+)', score_text)
            if not score_match:
                score_match = re.search(r'(\d+)[:\-–—](\d+)', score_text)
            if score_match:
                try:
                    score1, score2 = int(score_match.group(1)), int(score_match.group(2))
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
                    if score1 >= 0 and score2 >= 0 and score1 <= 10 and score2 <= 10:
                        a_score, b_score = score1, score2
                except ValueError:
                    pass
    
    return a_score, b_score


def extract_tournament_info(soup: BeautifulSoup, url: str) -> Tuple[str, str, str]:
    """
    Extract tournament name, stage, and match name from match page.
    
    Args:
        soup: BeautifulSoup parsed HTML
        url: Match URL (for fallback)
    
    Returns:
        Tuple of (tournament, stage, match_name)
    """
    match_name_elem = soup.select_one('.match-header-event, .match-header .event, [class*="event"]')
    match_name = ''
    if match_name_elem:
        match_name = match_name_elem.get_text(' ', strip=True)
    
    # Fallback: try to get from page title
    if not match_name or len(match_name) < 5:
        title_elem = soup.find('title')
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            if ' - ' in title_text:
                parts = title_text.split(' - ', 1)
                if len(parts) > 1:
                    match_name = parts[1].split(' | ')[0].strip()
            elif ' | ' in title_text:
                match_name = title_text.split(' | ')[0].strip()
            else:
                match_name = title_text.strip()
    
    # Additional fallback: try breadcrumbs
    if not match_name or len(match_name) < 5:
        breadcrumb = soup.select_one('.breadcrumb, .wf-breadcrumb, nav[aria-label="Breadcrumb"], [class*="breadcrumb"]')
        if breadcrumb:
            breadcrumb_text = breadcrumb.get_text(' ', strip=True)
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
    parts = [p.strip() for p in match_name.split(':')]
    if parts:
        tournament = parts[0].strip()
    
    # Extract stage
    if len(parts) >= 2:
        for part in parts[1:-1] if len(parts) > 2 else parts[1:]:
            stage_match = re.search(r'(Main Event|Group Stage|Swiss Stage|Playoffs|Knockout Stage|Stage\s*[12]|Kickoff|Regular Season)', part, re.IGNORECASE)
            if stage_match:
                stage = stage_match.group(1)
                break
            if part and not stage:
                stage = part
    
    # Fallback: try to get tournament from breadcrumbs
    if not tournament or len(tournament) < 3:
        breadcrumb = soup.select_one('.breadcrumb, .wf-breadcrumb, nav[aria-label="Breadcrumb"]')
        if breadcrumb:
            breadcrumb_text = breadcrumb.get_text(' ', strip=True)
            if 'VCT' in breadcrumb_text or 'Champions Tour' in breadcrumb_text:
                parts = breadcrumb_text.split()
                for i, part in enumerate(parts):
                    if 'VCT' in part or 'Champions' in part:
                        tournament = ' '.join(parts[i:min(i+5, len(parts))])
                        break
    
    return tournament, stage, match_name


def detect_showmatch(soup: BeautifulSoup, match_name: str) -> bool:
    """
    Detect if a match is a showmatch.
    
    Args:
        soup: BeautifulSoup parsed HTML
        match_name: Match name/title
    
    Returns:
        True if match is a showmatch
    """
    # Check HTML element
    showmatch_elem = soup.select_one('.match-header-event-series, [class*="event-series"]')
    if showmatch_elem:
        series_text = showmatch_elem.get_text(' ', strip=True).lower()
        if 'showmatch' in series_text:
            return True
    
    # Check match name
    if match_name:
        match_name_lower = match_name.lower()
        if 'showmatch' in match_name_lower or 'show match' in match_name_lower or 'show-match' in match_name_lower:
            return True
    
    return False


def extract_match_metadata(soup: BeautifulSoup, match_id: int, url: str) -> dict:
    """
    Extract all match-level metadata from a match page.
    
    Args:
        soup: BeautifulSoup parsed HTML
        match_id: Match ID
        url: Match URL
    
    Returns:
        Dictionary with match metadata:
        - match_id
        - tournament
        - stage
        - match_name
        - team_a
        - team_b
        - team_a_score
        - team_b_score
        - match_ts_utc
        - match_date
        - is_showmatch
    """
    team_a, team_b = extract_teams(soup)
    a_score, b_score = extract_match_scores(soup)
    tournament, stage, match_name = extract_tournament_info(soup, url)
    dt_utc = extract_match_datetime(soup)
    date_str = dt_utc[:10] if dt_utc else None
    is_showmatch = detect_showmatch(soup, match_name)
    
    return {
        'match_id': match_id,
        'tournament': tournament,
        'stage': stage,
        'match_name': match_name,
        'team_a': team_a,
        'team_b': team_b,
        'team_a_score': a_score,
        'team_b_score': b_score,
        'match_ts_utc': dt_utc,
        'match_date': date_str,
        'is_showmatch': is_showmatch,
    }
