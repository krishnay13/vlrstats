#!/usr/bin/env python3
"""
Normalize team names in database to use correct canonical forms.
Maps wrong names to correct ones.
"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "valorant_esports.db"

# Mapping of wrong names to correct canonical names
CORRECTIONS = {
    "DeToNator": "DetonativoN FocusMe",
    "KC": "Karmine Corp",
    "Nongshim Esports": "Nongshim Redforce",
    "Vitality": "Team Vitality",
    "FUR Esports": "Furia Esports",
}

def normalize_team_names():
    """Normalize team names in database to correct canonical forms."""
    db = sqlite3.connect(DB_PATH)
    cursor = db.cursor()
    
    for wrong_name, correct_name in CORRECTIONS.items():
        # Check how many records need updating
        cursor.execute(
            "SELECT COUNT(*) FROM Player_Stats WHERE team = ?",
            (wrong_name,)
        )
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"Updating {count} records: '{wrong_name}' -> '{correct_name}'")
            cursor.execute(
                "UPDATE Player_Stats SET team = ? WHERE team = ?",
                (correct_name, wrong_name)
            )
            
            # Also update Matches table if needed
            cursor.execute(
                "UPDATE Matches SET team_a = ? WHERE team_a = ?",
                (correct_name, wrong_name)
            )
            cursor.execute(
                "UPDATE Matches SET team_b = ? WHERE team_b = ?",
                (correct_name, wrong_name)
            )
        else:
            print(f"No records found for '{wrong_name}'")
    
    db.commit()
    
    # Verify the changes
    print("\nVerifying updates:")
    for correct_name in CORRECTIONS.values():
        cursor.execute(
            "SELECT COUNT(*) FROM Player_Stats WHERE team = ?",
            (correct_name,)
        )
        count = cursor.fetchone()[0]
        print(f"  '{correct_name}': {count} records")
    
    db.close()
    print("\nNormalization complete!")

if __name__ == "__main__":
    normalize_team_names()
