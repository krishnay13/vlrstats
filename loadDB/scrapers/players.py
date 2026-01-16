"""
Player statistics extraction from VLR.gg match pages.

Extracts player performance data:
- Player names and teams
- Agent selections
- Rating, ACS, K/D/A stats
"""
from bs4 import BeautifulSoup
from typing import List, Tuple, Optional
from ..normalizers.team import normalize_team


def _first_num(text: str, default: float = 0.0, as_int: bool = False) -> float | int:
    """
    Extract first number from text.
    
    Args:
        text: Text to parse
        default: Default value if no number found
        as_int: If True, return as integer
    
    Returns:
        Extracted number
    """
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


def parse_player_row(row, match_id: int, game_id: str) -> Optional[Tuple]:
    """
    Parse a single player stat row from the stats table.
    
    Args:
        row: BeautifulSoup table row element
        match_id: Match ID
        game_id: Game/Map ID
    
    Returns:
        Tuple of (match_id, game_id, player, team, agent, rating, acs, kills, deaths, assists, first_kills, first_deaths)
        or None if row is invalid
    """
    cells = row.find_all('td')
    if len(cells) < 9:  # Increased to 9 to include FK and FD cells
        return None
    
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
                # Try to extract from cell text
                cell_text = player_cell.get_text('\n', strip=True)
                lines = [l.strip() for l in cell_text.split('\n') if l.strip()]
                if len(lines) > 1:
                    team = lines[1]
    
    if not player:
        return None
    
    # Normalize team name using aliases
    team = normalize_team(team) if team else 'Unknown'
    
    # Extract agent from image
    img = row.find('img')
    agent = None
    if img:
        agent = img.get('title') or img.get('alt') or img.get('data-title')
        if not agent:
            img_parent = img.parent
            if img_parent:
                agent = img_parent.get('title') or img_parent.get_text(strip=True)
    
    # Extract stats
    rating = _first_num(cells[2].get_text(), 0.0)
    acs = _first_num(cells[3].get_text(), 0, as_int=True)
    kills = _first_num(cells[4].get_text(), 0, as_int=True)
    deaths = _first_num(cells[5].get_text(), 0, as_int=True)
    assists = _first_num(cells[6].get_text(), 0, as_int=True)
    
    # Extract first kills and first deaths from mod-fb and mod-fd cells
    # These are at cells[11] and cells[12] in the overview table
    first_kills = 0
    first_deaths = 0
    
    if len(cells) > 11:
        # cells[11] should be mod-fb (first blood/kills)
        fb_cell = cells[11]
        if 'mod-fb' in fb_cell.get('class', []):
            first_kills = _first_num(fb_cell.get_text(), 0, as_int=True)
    
    if len(cells) > 12:
        # cells[12] should be mod-fd (first death)
        fd_cell = cells[12]
        if 'mod-fd' in fd_cell.get('class', []):
            first_deaths = _first_num(fd_cell.get_text(), 0, as_int=True)
    
    return (match_id, game_id, player, team, agent or 'Unknown', rating, acs, kills, deaths, assists, first_kills, first_deaths)


def extract_player_stats(soup: BeautifulSoup, match_id: int) -> List[Tuple]:
    """
    Extract all player statistics for a match.
    
    Args:
        soup: BeautifulSoup parsed HTML
        match_id: Match ID
    
    Returns:
        List of tuples: (match_id, game_id, player, team, agent, rating, acs, kills, deaths, assists, first_kills, first_deaths)
    """
    players_info = []
    
    for game_div in soup.select('div.vm-stats-game'):
        game_id = game_div.get('data-game-id')
        if not game_id or game_id == 'all':
            continue
        
        # Find tables in this game div - look for both tbody tr and direct tr
        tables = game_div.find_all('table', class_='wf-table-inset')
        if not tables:
            continue
        
        for table in tables:
            # Try tbody first, then direct tr
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
            else:
                rows = table.find_all('tr')
            
            # Skip header row if present
            for row in rows:
                # Check if this is a header row (has th elements)
                if row.find('th'):
                    continue
                player_info = parse_player_row(row, match_id, game_id)
                if player_info:
                    players_info.append(player_info)
    
    return players_info
