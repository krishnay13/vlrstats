#!/usr/bin/env python3
"""
Normalize all team names in the Player_Stats table to canonical forms.
Uses the aliases mapping from aliases/teams.json to ensure consistency.
"""

import json
import sqlite3
from pathlib import Path

def load_team_aliases():
    """Load team aliases from the aliases/teams.json file."""
    aliases_path = Path(__file__).parent / 'aliases' / 'teams.json'
    with open(aliases_path, 'r') as f:
        return json.load(f)

def normalize_team_names():
    """Normalize all team names in the Player_Stats table."""
    
    # Load aliases
    aliases = load_team_aliases()
    
    # Create reverse mapping: variant -> canonical
    variant_to_canonical = {}
    for variant, canonical in aliases.items():
        variant_to_canonical[variant.lower().strip()] = canonical
    
    # Connect to database
    # Check multiple possible locations
    possible_paths = [
        Path(__file__).parent.parent / 'valorant_esports.db',
        Path(__file__).parent.parent / 'instance' / 'vlr_stat.db',
        Path(__file__).parent.parent / 'frontend' / 'valorant_esports.db',
    ]
    
    db_path = None
    for path in possible_paths:
        if path.exists():
            db_path = path
            break
    
    if db_path is None:
        print(f"Error: Database not found. Searched:")
        for path in possible_paths:
            print(f"  - {path}")
        return
    
    print(f"Using database: {db_path}\n")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Get all unique team names from Player_Stats
        cursor.execute("SELECT DISTINCT team FROM Player_Stats WHERE team IS NOT NULL")
        teams_in_db = [row[0] for row in cursor.fetchall()]
        
        print(f"Found {len(teams_in_db)} unique teams in Player_Stats")
        print("\nTeams found in database:")
        for team in sorted(teams_in_db):
            print(f"  - {team}")
        
        # Normalize each team
        print("\n" + "="*80)
        print("Normalizing teams...")
        print("="*80)
        
        normalization_count = 0
        for team in teams_in_db:
            variant_lower = team.lower().strip()
            
            # Check if this team needs normalization
            if variant_lower in variant_to_canonical:
                canonical = variant_to_canonical[variant_lower]
                
                # Only update if it's different
                if team != canonical:
                    # Count rows to update
                    cursor.execute("SELECT COUNT(*) FROM Player_Stats WHERE team = ?", (team,))
                    count = cursor.fetchone()[0]
                    
                    # Update
                    cursor.execute("UPDATE Player_Stats SET team = ? WHERE team = ?", (canonical, team))
                    conn.commit()
                    
                    print(f"✓ Updated {count:4d} records: '{team}' → '{canonical}'")
                    normalization_count += 1
            else:
                # Team not in aliases - check if it's already canonical
                canonical_found = False
                for variant, canonical in variant_to_canonical.items():
                    if team == canonical:
                        canonical_found = True
                        break
                
                if not canonical_found:
                    # Special case: Check for KRÜ which might have encoding issues
                    # Try matching case-insensitive for known teams
                    team_lower = team.lower().strip()
                    if team_lower == 'krü' or team == 'KRÜ':
                        canonical = 'KRÜ Esports'
                        cursor.execute("SELECT COUNT(*) FROM Player_Stats WHERE team = ?", (team,))
                        count = cursor.fetchone()[0]
                        cursor.execute("UPDATE Player_Stats SET team = ? WHERE team = ?", (canonical, team))
                        conn.commit()
                        print(f"✓ Updated {count:4d} records: '{team}' → '{canonical}'")
                        normalization_count += 1
                    else:
                        print(f"⚠ Unknown team (no mapping): '{team}'")
        
        print("\n" + "="*80)
        print(f"Normalization complete! Updated {normalization_count} team variants")
        print("="*80)
        
        # Verify results
        print("\nFinal teams in database:")
        cursor.execute("SELECT DISTINCT team FROM Player_Stats WHERE team IS NOT NULL ORDER BY team")
        final_teams = [row[0] for row in cursor.fetchall()]
        for team in final_teams:
            cursor.execute("SELECT COUNT(*) FROM Player_Stats WHERE team = ?", (team,))
            count = cursor.fetchone()[0]
            print(f"  - {team}: {count} records")
        
    finally:
        conn.close()

if __name__ == '__main__':
    normalize_team_names()
