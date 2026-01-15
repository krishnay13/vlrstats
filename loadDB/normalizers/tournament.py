"""
Tournament/Event name normalization.

Applies tournament aliases and provides additional normalization logic.
"""
import re
from ..aliases import normalize_tournament as alias_normalize_tournament


def normalize_tournament(name: str) -> str:
    """
    Normalize a tournament name using aliases.
    
    Args:
        name: Tournament name to normalize
    
    Returns:
        Normalized tournament name
    """
    if not name:
        return ""
    
    # Apply aliases
    normalized = alias_normalize_tournament(name)
    
    # Additional normalization: clean up whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()
    
    return normalized
