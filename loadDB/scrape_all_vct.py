"""
Main script to clear database and scrape all VCT 2024 and 2025 matches.
"""
import asyncio
import sys
import os
import sqlite3
from datetime import datetime
from .vct_scraper import scrape_all_vct_matches, classify_matches, detect_showmatch
from .vlr_ingest import ingest
from .db_utils import get_conn
from .config import DB_PATH


def backup_database(db_path: str = None):
    """Create backup of existing database before clearing."""
    db_path = db_path or DB_PATH
    if os.path.exists(db_path):
        backup_name = f'valorant_esports_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        import shutil
        shutil.copy2(db_path, backup_name)
        print(f"[OK] Backup created: {backup_name}")
        return backup_name
    return None


def clear_database(db_path: str = None):
    """Clear all data from database tables."""
    db_path = db_path or DB_PATH
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    tables_to_clear = [
        'Elo_History',
        'Player_Elo_History',
        'Elo_Current',
        'Player_Elo_Current',
        'Player_Stats',
        'Maps',
        'Matches',
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
    for table in ['Matches']:
        try:
            cur.execute(f'SELECT COUNT(*) FROM {table}')
            count = cur.fetchone()[0]
            print(f"  {table}: {count} rows")
        except:
            pass
    
    con.close()
    print("[OK] Database cleared")


async def main(confirm: bool = True):
    print("=" * 70)
    print("VCT 2024 & 2025 COMPLETE SCRAPE")
    print("=" * 70)
    print("\nThis script will:")
    print("  1. Backup the current database")
    print("  2. Clear all existing data")
    print("  3. Scrape all VCT 2024 tournaments")
    print("  4. Scrape all VCT 2025 tournaments")
    print("  5. Classify matches (VCT vs SHOWMATCH)")
    print("  6. Ingest all matches into the database")
    print()
    
    if confirm:
        try:
            response = input("Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("Operation cancelled.")
                return
        except EOFError:
            # Non-interactive mode, proceed automatically
            print("Non-interactive mode: proceeding automatically...")
    else:
        print("Proceeding automatically (non-interactive mode)...")
    
    # Step 1: Backup database
    print("\n" + "=" * 70)
    print("STEP 1: Backing up database...")
    print("=" * 70)
    backup_database()
    
    # Step 2: Clear database
    print("\n" + "=" * 70)
    print("STEP 2: Clearing database...")
    print("=" * 70)
    clear_database()
    
    # Step 3 & 4: Scrape all tournaments
    print("\n" + "=" * 70)
    print("STEP 3 & 4: Scraping all VCT tournaments...")
    print("=" * 70)
    results = await scrape_all_vct_matches()
    
    # Combine all matches
    all_matches = results['vct_2024'] + results['vct_2025']
    print(f"\nTotal matches found: {len(all_matches)}")
    
    # Step 5 & 6: Ingest matches (classification happens during ingestion)
    print("\n" + "=" * 70)
    print("STEP 5 & 6: Ingesting matches into database (auto-classifying)...")
    print("=" * 70)
    
    # Extract just match IDs
    all_match_ids = [match_id for match_id, _ in all_matches]
    
    print(f"\nIngesting {len(all_match_ids)} matches...")
    print("(Matches will be auto-classified as VCT or SHOWMATCH during ingestion)")
    
    # Process in batches to avoid overwhelming the system
    batch_size = 50
    total_batches = (len(all_match_ids) + batch_size - 1) // batch_size
    
    for i in range(0, len(all_match_ids), batch_size):
        batch = all_match_ids[i:i+batch_size]
        batch_num = i//batch_size + 1
        print(f"  Processing batch {batch_num}/{total_batches} ({len(batch)} matches)...")
        try:
            # Pass None to let auto-detection work
            ingest(batch, match_type=None)
            print(f"    [OK] Ingested {len(batch)} matches")
        except Exception as e:
            print(f"    [ERROR] Error ingesting batch: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("SCRAPING COMPLETE!")
    print("=" * 70)
    
    # Verify database
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM Matches")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Matches WHERE match_type = 'VCT'")
    vct_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Matches WHERE match_type = 'SHOWMATCH'")
    showmatch_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Matches WHERE match_type IS NULL OR match_type = ''")
    null_count = cur.fetchone()[0]
    conn.close()
    
    print(f"\nDatabase verification:")
    print(f"  Total matches in DB: {total}")
    print(f"  VCT matches: {vct_count}")
    print(f"  SHOWMATCH matches: {showmatch_count}")
    if null_count > 0:
        print(f"  Unclassified matches: {null_count}")


if __name__ == '__main__':
    asyncio.run(main())
