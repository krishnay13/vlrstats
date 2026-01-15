"""
Map data extraction from VLR.gg match pages.

Extracts map information including:
- Map names
- Map scores
- Game IDs
"""
import re
from bs4 import BeautifulSoup
from typing import List, Tuple, Optional
from ..normalizers.map import normalize_map


def extract_map_name(game_div, soup: BeautifulSoup) -> str:
    """
    Extract map name from a game div.
    
    Args:
        game_div: BeautifulSoup element for the game/map
        soup: Full page soup for fallback
    
    Returns:
        Map name (normalized)
    """
    header = game_div.find('div', class_='vm-stats-game-header')
    map_name = None
    
    if header:
        name_elem = header.find(class_='map')
        if name_elem:
            map_name = name_elem.get_text(strip=True)
    
    if not map_name:
        game_id = game_div.get('data-game-id')
        nav_item = soup.find('a', class_='vm-stats-gamesnav-item', attrs={'data-game-id': game_id})
        map_name = nav_item.get_text(strip=True) if nav_item else 'Unknown'
    
    # Normalize using alias system
    return normalize_map(map_name or 'Unknown')


def extract_map_scores(game_div, team_a: str, team_b: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Extract map scores from a game div.
    
    Uses multiple strategies to find scores, with fallbacks.
    
    Args:
        game_div: BeautifulSoup element for the game/map
        team_a: Team A name (for context)
        team_b: Team B name (for context)
    
    Returns:
        Tuple of (team_a_score, team_b_score) or (None, None) if not found
    """
    header = game_div.find('div', class_='vm-stats-game-header')
    if not header:
        return None, None
    
    a_map_score = b_map_score = None
    
    # Strategy 1: Extract from score elements in team containers
    score_elems = []
    team_containers = header.select('div.team, div[class*="team"]')
    
    for team_container in team_containers:
        classes = team_container.get('class', [])
        if classes:
            class_str = ' '.join(classes) if isinstance(classes, list) else str(classes)
            if 'team-name' in class_str.lower():
                continue
        
        score_elem = team_container.select_one('div.score, div[class*="score"]')
        if score_elem:
            score_elems.append(score_elem)
    
    if not score_elems:
        score_elems = header.select('div.score, div[class*="score"]')
    
    # Extract scores from found elements
    if score_elems:
        scores = []
        for score_elem in score_elems:
            score_text = score_elem.get_text(strip=True)
            try:
                score_num = int(score_text)
                if score_num >= 0:
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
        
        if len(scores) >= 2:
            scores.sort(key=lambda x: x[1])  # False (left) before True (right)
            a_map_score, b_map_score = scores[0][0], scores[1][0]
        elif len(scores) == 1:
            score_num, is_right, _ = scores[0]
            if is_right:
                b_map_score = score_num
            else:
                a_map_score = score_num
    
    # Strategy 2: Extract from header text with regex
    if (a_map_score is None or b_map_score is None) and header:
        header_text = header.get_text(' ', strip=True)
        header_clean = re.sub(r'\d+:\d{2}:\d{2}', ' ', header_text)
        header_clean = re.sub(r'\d+:\d{2}(?!\d)', ' ', header_clean)
        
        score_match = re.search(r'(\d{1,2})\s*[:\-–—]\s*(\d{1,2})', header_clean)
        if score_match:
            score1, score2 = int(score_match.group(1)), int(score_match.group(2))
            if score1 >= 0 and score2 >= 0 and (score1 >= 13 or score2 >= 13):
                # Simple assignment: first score is team A
                a_map_score, b_map_score = score1, score2
    
    # Validate scores
    if a_map_score is not None and b_map_score is not None:
        total = a_map_score + b_map_score
        max_score = max(a_map_score, b_map_score)
        
        if max_score < 13 or total < 13 or a_map_score < 0 or b_map_score < 0:
            a_map_score, b_map_score = None, None
        elif max_score == min(a_map_score, b_map_score) and max_score < 13:
            a_map_score, b_map_score = None, None
    
    return a_map_score, b_map_score


def extract_maps(soup: BeautifulSoup, match_id: int, team_a: str, team_b: str) -> List[Tuple[int, str, str, Optional[int], Optional[int]]]:
    """
    Extract all maps for a match.
    
    Args:
        soup: BeautifulSoup parsed HTML
        match_id: Match ID
        team_a: Team A name
        team_b: Team B name
    
    Returns:
        List of tuples: (match_id, game_id, map_name, team_a_score, team_b_score)
    """
    maps_info = []
    
    for game_div in soup.select('div.vm-stats-game'):
        game_id = game_div.get('data-game-id')
        if not game_id or game_id == 'all':
            continue
        
        map_name = extract_map_name(game_div, soup)
        a_map_score, b_map_score = extract_map_scores(game_div, team_a, team_b)
        
        maps_info.append((match_id, game_id, map_name, a_map_score, b_map_score))
    
    return maps_info
