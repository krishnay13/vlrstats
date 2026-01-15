"""
Map name normalization.

Applies map aliases and provides additional normalization logic.
"""
import re
from ..aliases import normalize_map as alias_normalize_map

# Known map names for validation
KNOWN_MAPS = [
    'Ascent', 'Bind', 'Breeze', 'Fracture', 'Haven', 'Icebox',
    'Lotus', 'Pearl', 'Split', 'Sunset', 'Abyss', 'Corrode'
]


def normalize_map(name: str) -> str:
    """
    Normalize a map name using aliases and known map list.
    
    Args:
        name: Map name to normalize
    
    Returns:
        Normalized map name
    """
    if not name:
        return "Unknown"
    
    # Apply aliases first
    normalized = alias_normalize_map(name)
    
    # If alias didn't match, try to find in known maps
    if normalized == name.strip():
        name_lower = name.lower().strip()
        for known_map in KNOWN_MAPS:
            if re.search(rf"\b{re.escape(known_map.lower())}\b", name_lower):
                return known_map
        
        # Clean up the name: remove extra whitespace, dashes
        cleaned = re.sub(r"\s+", " ", normalized).strip('- ').strip()
        if cleaned:
            return cleaned
    
    return normalized.strip()
