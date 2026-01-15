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
        Tuple of (match_id, game_id, player, team, agent, rating, acs, kills, deaths, assists)
        or None if row is invalid
    """
    cells = row.find_all('td')
    if len(cells) < 7:
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
    
    return (match_id, game_id, player, team, agent or 'Unknown', rating, acs, kills, deaths, assists)


def extract_player_stats(soup: BeautifulSoup, match_id: int) -> List[Tuple]:
    """
    Extract all player statistics for a match.
    
    Args:
        soup: BeautifulSoup parsed HTML
        match_id: Match ID
    
    Returns:
        List of tuples: (match_id, game_id, player, team, agent, rating, acs, kills, deaths, assists)
    """
    players_info = []
    
    for game_div in soup.select('div.vm-stats-game'):
        game_id = game_div.get('data-game-id')
        if not game_id or game_id == 'all':
            continue
        
        # Only process if we have a valid stats table
        if not game_div.select('table.wf-table-inset tbody tr'):
            continue
        
        for row in game_div.select('table.wf-table-inset tbody tr'):
            player_info = parse_player_row(row, match_id, game_id)
            if player_info:
                players_info.append(player_info)
    
    return players_info
