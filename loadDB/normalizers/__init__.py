"""
Normalizer modules for applying aliases to entity names.

Each normalizer applies aliases from the unified alias system
and provides additional normalization logic specific to that entity type.
"""
from .team import normalize_team
from .map import normalize_map
from .tournament import normalize_tournament
from .match_type import normalize_match_type

__all__ = [
    "normalize_team",
    "normalize_map",
    "normalize_tournament",
    "normalize_match_type",
]
