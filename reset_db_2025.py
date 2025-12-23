"""
Reset database and prepare for fresh 2025 VCT data.
Clears all 2024 data and reinitializes schema.
"""
import sqlite3
import os
from datetime import datetime


def backup_database(db_path='valorant_esports.db'):
    """Create backup of existing database before clearing."""
    if os.path.exists(db_path):
        backup_name = f'valorant_esports_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        import shutil
        shutil.copy2(db_path, backup_name)
        print(f"✓ Backup created: {backup_name}")
        return backup_name
    return None


def clear_database(db_path='valorant_esports.db'):
    """Clear all data from database tables."""
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    tables_to_clear = [
        'EloHistoryPlayer',
        'EloHistoryTeam',
        'Player_Stats',
        'Maps',
        'Matches',
        'Players',
        'Teams'
    ]
    
    print("Clearing database tables...")
    for table in tables_to_clear:
        try:
            cur.execute(f'DELETE FROM {table}')
            print(f"  ✓ Cleared {table}")
        except sqlite3.OperationalError as e:
            print(f"  ⚠ {table}: {e}")
    
    con.commit()
    
    # Get counts
    for table in ['Matches', 'Players', 'Teams']:
        try:
            cur.execute(f'SELECT COUNT(*) FROM {table}')
            count = cur.fetchone()[0]
            print(f"  {table}: {count} rows")
        except:
            pass
    
    con.close()
    print("✓ Database cleared and ready for 2025 data")


if __name__ == '__main__':
    print("=" * 70)
    print("DATABASE RESET FOR 2025 VCT SEASON")
    print("=" * 70)
    
    response = input("\nThis will DELETE all 2024 data. Continue? (yes/no): ")
    if response.lower() == 'yes':
        backup_database()
        clear_database()
        print("\n✓ Database is now ready for fresh 2025 VCT data")
        print("\nNext steps:")
        print("  1. Run: python loadDB/scrape_2025_fresh.py")
        print("  2. Load scraped matches into DB")
        print("  3. Recalculate Elo: python -c \"from analytics.elo import EloEngine; EloEngine().recalc_from_history()\"")
        print("  4. Train models: python -m analytics.train")
    else:
        print("Operation cancelled.")
