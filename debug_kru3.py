#!/usr/bin/env python3
"""
Debug normalize_team_names script flow for KRÜ
"""

import json
from pathlib import Path

# Load aliases
aliases_path = Path(__file__).parent / 'loadDB' / 'aliases' / 'teams.json'
with open(aliases_path, 'r', encoding='utf-8') as f:
    aliases = json.load(f)

# Create reverse mapping: variant -> canonical
variant_to_canonical = {}
for variant, canonical in aliases.items():
    variant_to_canonical[variant.lower().strip()] = canonical

# Simulate what happens with 'KRÜ'
team = 'KRÜ'
variant_lower = team.lower().strip()

print(f"Team from DB: {repr(team)}")
print(f"Variant lower: {repr(variant_lower)}")
print(f"In variant_to_canonical: {variant_lower in variant_to_canonical}")

if variant_lower in variant_to_canonical:
    canonical = variant_to_canonical[variant_lower]
    print(f"Canonical found: {repr(canonical)}")
    
    if team != canonical:
        print(f"Team {repr(team)} != Canonical {repr(canonical)} -> SHOULD UPDATE")
    else:
        print(f"Team {repr(team)} == Canonical {repr(canonical)} -> NO UPDATE")
else:
    # Check if it's already canonical
    canonical_found = False
    for variant, canonical in variant_to_canonical.items():
        if team == canonical:
            canonical_found = True
            print(f"Team {repr(team)} is already canonical")
            break
    
    if not canonical_found:
        print(f"⚠ Unknown team (no mapping): {repr(team)}")
