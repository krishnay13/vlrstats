"""
Team name normalization.

Applies team aliases and provides additional normalization logic.
Optionally uses LLM for unknown team names.
"""
import os
from ..aliases import normalize_team as alias_normalize_team


def normalize_team(name: str, use_llm: bool = False) -> str:
    """
    Normalize a team name using aliases.
    
    Args:
        name: Team name to normalize
        use_llm: If True, use LLM to normalize unknown teams (requires ANTHROPIC_API_KEY)
    
    Returns:
        Normalized team name
    """
    if not name:
        return ""
    
    # Apply aliases
    normalized = alias_normalize_team(name)
    
    # If the name didn't change (no alias found) and LLM is enabled, try LLM normalization
    if use_llm and normalized.lower() == name.lower() and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from ..llm_normalize import normalize_team_with_llm
            from ..aliases.teams import TEAM_ALIASES
            llm_normalized = normalize_team_with_llm(name, TEAM_ALIASES)
            if llm_normalized and llm_normalized != name:
                print(f"LLM normalized: '{name}' -> '{llm_normalized}'")
                normalized = llm_normalized
        except Exception as e:
            print(f"LLM normalization skipped for '{name}': {e}")
    
    # Additional normalization: trim whitespace
    return normalized.strip()
