"""
Match type normalization.

Applies match type aliases and provides additional normalization logic.
"""
from ..aliases import normalize_match_type as alias_normalize_match_type


def normalize_match_type(name: str) -> str:
    """
    Normalize a match type using aliases.
    
    Valid match types: VCT, VCL, OFFSEASON, SHOWMATCH
    
    Args:
        name: Match type to normalize
    
    Returns:
        Normalized match type (uppercase)
    """
    if not name:
        return ""
    
    # Apply aliases
    normalized = alias_normalize_match_type(name)
    
    # Ensure uppercase for consistency
    normalized = normalized.upper().strip()
    
    # Validate it's a known match type
    valid_types = {"VCT", "VCL", "OFFSEASON", "SHOWMATCH"}
    if normalized not in valid_types:
        # Try to infer from the name
        name_lower = normalized.lower()
        if "showmatch" in name_lower or "show match" in name_lower:
            return "SHOWMATCH"
        elif "vcl" in name_lower or "challengers" in name_lower:
            return "VCL"
        elif "offseason" in name_lower or "off-season" in name_lower:
            return "OFFSEASON"
        elif "vct" in name_lower or "champions tour" in name_lower:
            return "VCT"
        # Default to VCT if unclear
        return "VCT"
    
    return normalized
