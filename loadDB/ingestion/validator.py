"""
Data validation for ingested matches.

Validates match data for consistency and completeness before database insertion.
"""
from typing import Tuple, List


def validate_match_data(
    match_row: tuple,
    maps_info: list,
    players_info: list
) -> Tuple[bool, List[str]]:
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
                total = ta_score + tb_score
                max_score = max(ta_score, tb_score)
                min_score = min(ta_score, tb_score)
                
                if ta_score < 0 or tb_score < 0 or max_score < 13 or total < 13:
                    warnings.append(f"Unusual map scores: {map_name} {ta_score}-{tb_score}")
                elif ta_score == tb_score and ta_score > 0 and ta_score < 13:
                    warnings.append(f"Map appears to be a draw: {map_name} {ta_score}-{tb_score}")
    
    # Validate player stats
    if not players_info:
        warnings.append("No player stats found for match")
    else:
        for player_info in players_info:
            _, _, player, team, agent, rating, acs, kills, deaths, assists = player_info
            if not player or player == 'Unknown':
                warnings.append("Player with unknown name found")
            if rating < 0 or rating > 5:
                warnings.append(f"Unusual rating for {player}: {rating}")
            if acs < 0 or acs > 500:
                warnings.append(f"Unusual ACS for {player}: {acs}")
    
    return is_valid, warnings
