#!/usr/bin/env python3
"""
Ingest the next completed upcoming match.

When a match you've been tracking completes, simply run this script
and it will automatically find and ingest the earliest completed match
from your upcoming matches list.

Usage:
    python ingest_next_completed.py
    python ingest_next_completed.py --no-validate  # Skip data validation
"""
import sys
import argparse
import asyncio
from loadDB.db_utils import get_conn
from loadDB import vlr_ingest
from loadDB import upcoming


def main():
    parser = argparse.ArgumentParser(
        description="Ingest the next completed upcoming match",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ingest_next_completed.py
      Find and ingest the earliest completed match from upcoming matches
  
  python ingest_next_completed.py --no-validate
      Ingest without data validation (faster)
        """
    )
    parser.add_argument("--no-validate", action="store_true", help="Skip data validation during ingestion")
    parser.add_argument("--no-refresh-upcoming", action="store_true", help="Skip refreshing upcoming matches before selecting the next one")
    parser.add_argument("--reset-pointer", action="store_true", help="Reset the upcoming pointer and start from the earliest null-score match")
    args = parser.parse_args()
    
    # Query the next upcoming match that has not been ingested yet (null scores)
    conn = get_conn()
    cur = conn.cursor()

    # Optionally refresh upcoming matches first so new IDs are available
    if not args.no_refresh_upcoming:
        print("Refreshing upcoming matches (VCT 2026 Kickoff events)...")
        try:
            asyncio.run(upcoming.main())
        except Exception as e:
            print(f"Warning: upcoming refresh failed: {e}")
    
    # Ensure a small state table and a partial index exist to speed up scans
    cur.execute("""
        CREATE TABLE IF NOT EXISTS IngestionState (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    # Partial index: earliest upcoming (null-score) by timestamp
    try:
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_matches_nullscore_ts
            ON Matches(match_ts_utc)
            WHERE team_a_score IS NULL AND team_b_score IS NULL
        """)
    except Exception:
        # Older SQLite versions may not support partial indexes; ignore
        pass

    # Read pointer (last processed upcoming match timestamp + id)
    cur.execute("SELECT value FROM IngestionState WHERE key = 'upcoming_pointer_ts'")
    row_ptr_ts = cur.fetchone()
    last_ts = row_ptr_ts[0] if row_ptr_ts and row_ptr_ts[0] else None

    cur.execute("SELECT value FROM IngestionState WHERE key = 'upcoming_pointer_id'")
    row_ptr_id = cur.fetchone()
    last_id = int(row_ptr_id[0]) if row_ptr_id and row_ptr_id[0] else None

    if args.reset_pointer:
        last_ts = None
        last_id = None
        cur.execute("DELETE FROM IngestionState WHERE key IN ('upcoming_pointer_ts', 'upcoming_pointer_id')")
        conn.commit()
        print("Pointer reset: will start from earliest null-score match.")

        # Select earliest upcoming match with NULL scores; order by ts then id
        if last_ts is not None and last_id is not None:
                cur.execute(
                        """
                        SELECT match_id, team_a, team_b, match_ts_utc
                        FROM Matches
                        WHERE match_ts_utc IS NOT NULL
                            AND team_a_score IS NULL
                            AND team_b_score IS NULL
                            AND (match_ts_utc > ? OR (match_ts_utc = ? AND match_id > ?))
                        ORDER BY match_ts_utc ASC, match_id ASC
                        LIMIT 1
                        """,
                        (last_ts, last_ts, last_id)
                )
        else:
                cur.execute(
                        """
                        SELECT match_id, team_a, team_b, match_ts_utc
                        FROM Matches
                        WHERE match_ts_utc IS NOT NULL
                            AND team_a_score IS NULL
                            AND team_b_score IS NULL
                        ORDER BY match_ts_utc ASC, match_id ASC
                        LIMIT 1
                        """
                )
    
    row = cur.fetchone()

    # If nothing found but pointer exists, reset pointer once and retry
    if not row and (last_ts is not None or last_id is not None):
        print("Pointer may be ahead of upcoming list; resetting pointer and retrying once...")
        cur.execute("DELETE FROM IngestionState WHERE key IN ('upcoming_pointer_ts', 'upcoming_pointer_id')")
        conn.commit()
        cur.execute(
            """
            SELECT match_id, team_a, team_b, match_ts_utc
            FROM Matches
            WHERE match_ts_utc IS NOT NULL
              AND team_a_score IS NULL
              AND team_b_score IS NULL
            ORDER BY match_ts_utc ASC, match_id ASC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        last_ts = None
        last_id = None

    if not row:
        conn.close()
        print("❌ No upcoming matches with NULL scores found.")
        print("Run 'python -m loadDB.upcoming' to refresh upcoming list.")
        return 0
    
    match_id, team_a, team_b, match_ts_utc = row
    
    print(f"\n✓ Next upcoming match to ingest:")
    print(f"  Match ID: {match_id}")
    print(f"  {team_a} vs {team_b}")
    print(f"  Scheduled: {match_ts_utc}")
    print(f"\n⏳ Ingesting match {match_id}...\n")
    
    # Ingest the match (use async ingest_matches so we can pass validate flag)
    asyncio.run(vlr_ingest.ingest_matches([match_id], validate=not args.no_validate))
    
    # Advance pointer to this match's timestamp and id
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO IngestionState(key, value) VALUES('upcoming_pointer_ts', ?)",
        (match_ts_utc,)
    )
    cur.execute(
        "INSERT OR REPLACE INTO IngestionState(key, value) VALUES('upcoming_pointer_id', ?)",
        (match_id,)
    )
    conn.commit()
    conn.close()
    
    print("\n✓ Done! Match has been ingested and Elo snapshots have been recalculated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
