"""
Unified alias system for normalizing entity names.

This module provides a centralized way to load and use aliases for:
- Teams
- Maps
- Tournaments/Events
- Match Types

All aliases are stored in JSON files and loaded at module import time.
"""
import json
import os
from typing import Dict, Literal, Optional

# Entity types that can have aliases
EntityType = Literal["team", "map", "tournament", "match_type"]

# Path to aliases directory
_ALIASES_DIR = os.path.dirname(__file__)

# Alias file mapping
_ALIAS_FILES: Dict[EntityType, str] = {
    "team": os.path.join(_ALIASES_DIR, "teams.json"),
    "map": os.path.join(_ALIASES_DIR, "maps.json"),
    "tournament": os.path.join(_ALIASES_DIR, "tournaments.json"),
    "match_type": os.path.join(_ALIASES_DIR, "match_types.json"),
}

# Cache for loaded aliases
_ALIAS_CACHE: Dict[EntityType, Dict[str, str]] = {}


def _load_alias_file(filepath: str) -> Dict[str, str]:
    """
    Load aliases from a JSON file.
    
    Args:
        filepath: Path to the JSON alias file
    
    Returns:
        Dictionary mapping lowercase variant names to canonical names
    """
    if not os.path.exists(filepath):
        return {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                # Normalize keys to lowercase for consistent lookups
                return {str(k).lower().strip(): str(v).strip() for k, v in data.items()}
    except Exception:
        pass
    
    return {}


def load_all_aliases() -> Dict[EntityType, Dict[str, str]]:
    """
    Load all alias files into a unified structure.
    
    Returns:
        Dictionary mapping entity types to their alias dictionaries
    """
    if _ALIAS_CACHE:
        return _ALIAS_CACHE
    
    for entity_type, filepath in _ALIAS_FILES.items():
        _ALIAS_CACHE[entity_type] = _load_alias_file(filepath)
    
    return _ALIAS_CACHE


def get_alias(entity_type: EntityType, name: str) -> Optional[str]:
    """
    Get canonical name for an entity using aliases.
    
    Args:
        entity_type: Type of entity (team, map, tournament, match_type)
        name: Variant name to look up
    
    Returns:
        Canonical name if alias exists, None otherwise
    """
    aliases = load_all_aliases()
    entity_aliases = aliases.get(entity_type, {})
    
    if not name:
        return None
    
    key = name.lower().strip()
    return entity_aliases.get(key)


def normalize_entity(entity_type: EntityType, name: str) -> str:
    """
    Normalize an entity name using aliases.
    
    If an alias exists, returns the canonical name.
    Otherwise, returns the original name (trimmed).
    
    Args:
        entity_type: Type of entity (team, map, tournament, match_type)
        name: Name to normalize
    
    Returns:
        Normalized canonical name
    """
    if not name:
        return ""
    
    canonical = get_alias(entity_type, name)
    if canonical:
        return canonical
    
    # Return original name trimmed
    return name.strip()


# Load aliases on module import
load_all_aliases()

# Convenience functions for each entity type
def normalize_team(name: str) -> str:
    """Normalize a team name using aliases."""
    return normalize_entity("team", name)


def normalize_map(name: str) -> str:
    """Normalize a map name using aliases."""
    return normalize_entity("map", name)


def normalize_tournament(name: str) -> str:
    """Normalize a tournament name using aliases."""
    return normalize_entity("tournament", name)


def normalize_match_type(name: str) -> str:
    """Normalize a match type using aliases."""
    return normalize_entity("match_type", name)


# Export for backward compatibility
def get_team_alias(name: str) -> Optional[str]:
    """Get team alias (backward compatibility)."""
    return get_alias("team", name)


# Export all aliases for inspection
def get_all_aliases() -> Dict[EntityType, Dict[str, str]]:
    """Get all loaded aliases."""
    return load_all_aliases().copy()
