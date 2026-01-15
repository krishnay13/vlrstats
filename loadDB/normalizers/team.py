"""
Team name normalization.

Applies team aliases and provides additional normalization logic.
"""
from ..aliases import normalize_team as alias_normalize_team


def normalize_team(name: str) -> str:
    """
    Normalize a team name using aliases.
    
    Args:
        name: Team name to normalize
    
    Returns:
        Normalized team name
    """
    if not name:
        return ""
    
    # Apply aliases
    normalized = alias_normalize_team(name)
    
    # Additional normalization: trim whitespace
    return normalized.strip()
