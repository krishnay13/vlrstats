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
from loadDB.db_utils import get_conn
from loadDB import vlr_ingest


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
    args = parser.parse_args()
    
    # Query the next upcoming match that has been completed (has scores)
    conn = get_conn()
    cur = conn.cursor()
    
    # Get first upcoming match with scores (ordered by match_ts_utc asc)
    cur.execute("""
        SELECT match_id, team_a, team_b, team_a_score, team_b_score, match_ts_utc
        FROM Matches
        WHERE match_ts_utc IS NOT NULL
        AND datetime(match_ts_utc, '+5 hours') > datetime('now')
        AND team_a_score IS NOT NULL
        AND team_b_score IS NOT NULL
        ORDER BY match_ts_utc ASC
        LIMIT 1
    """)
    
    row = cur.fetchone()
    conn.close()
    
    if not row:
        print("❌ No completed upcoming matches found.")
        print("Upcoming matches will be ingested once they have scores.")
        return 0
    
    match_id, team_a, team_b, ta_score, tb_score, match_ts_utc = row
    
    print(f"\n✓ Found completed upcoming match:")
    print(f"  Match ID: {match_id}")
    print(f"  {team_a} {ta_score}-{tb_score} {team_b}")
    print(f"  Time: {match_ts_utc}")
    print(f"\n⏳ Ingesting match {match_id}...\n")
    
    # Ingest the match
    vlr_ingest.ingest([match_id], validate=not args.no_validate)
    
    print("\n✓ Done! Match has been ingested and Elo snapshots have been recalculated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
