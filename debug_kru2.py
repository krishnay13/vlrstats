#!/usr/bin/env python3
"""
Debug: Check why KRÜ is not normalizing
"""

import json
from pathlib import Path

def load_team_aliases():
    """Load team aliases from the aliases/teams.json file."""
    aliases_path = Path(__file__).parent / 'loadDB' / 'aliases' / 'teams.json'
    with open(aliases_path, 'r', encoding='utf-8') as f:
        return json.load(f)

aliases = load_team_aliases()

# Create reverse mapping
variant_to_canonical = {}
for variant, canonical in aliases.items():
    variant_lower = variant.lower().strip()
    variant_to_canonical[variant_lower] = canonical

team = 'KRÜ'
variant_lower = team.lower().strip()

print(f"Team: {repr(team)}")
print(f"Lowercase: {repr(variant_lower)}")
print(f"In mapping: {variant_lower in variant_to_canonical}")
print(f"Mapped to: {variant_to_canonical.get(variant_lower, 'NOT FOUND')}")

# Show all kru variants
print("\nAll kru variants in aliases:")
for k, v in variant_to_canonical.items():
    if 'kru' in k or 'krü' in k:
        print(f"  {repr(k)} -> {repr(v)}")
