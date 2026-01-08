import sqlite3
from ..db_utils import get_conn, ensure_matches_columns
from ..backfill import backfill_match_dates_from_timestamps, backfill_missing_timestamps


def get_counts(conn: sqlite3.Connection) -> tuple[int, int, int]:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM Matches WHERE match_ts_utc IS NULL")
    missing_ts = int(cur.fetchone()[0] or 0)
    cur.execute("SELECT COUNT(*) FROM Matches WHERE match_date IS NULL OR match_date = ''")
    missing_date = int(cur.fetchone()[0] or 0)
    cur.execute("SELECT COUNT(*) FROM Matches")
    total = int(cur.fetchone()[0] or 0)
    return missing_ts, missing_date, total


def main(limit: int = 50) -> None:
    conn = get_conn()
    ensure_matches_columns(conn)
    before = get_counts(conn)
    print(f"Before: missing_ts={before[0]}, missing_date={before[1]}, total={before[2]}")
    conn.close()

    # Step 1: derive match_date from existing timestamps
    backfill_match_dates_from_timestamps()

    # Step 2: scrape and fill missing timestamps (limited)
    backfill_missing_timestamps(limit)

    # Step 3: re-derive match_date after new timestamps
    backfill_match_dates_from_timestamps()

    conn = get_conn()
    after = get_counts(conn)
    print(f"After:  missing_ts={after[0]}, missing_date={after[1]}, total={after[2]}")
    conn.close()


if __name__ == "__main__":
    main(50)
import os
import sqlite3
from loadDB.backfill import backfill_match_dates_from_timestamps, backfill_missing_timestamps

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'valorant_esports.db'))


def counts(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM Matches WHERE match_ts_utc IS NULL OR match_ts_utc = ''")
    ts_null = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Matches WHERE match_date IS NULL OR match_date = ''")
    date_null = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Matches")
    total = cur.fetchone()[0]
    return ts_null, date_null, total


def main(limit: int = 50):
    conn = sqlite3.connect(DB_PATH)
    print("Before:", counts(conn))
    conn.close()

    # First, derive dates where timestamps already exist
    backfill_match_dates_from_timestamps()

    # Next, try to fetch timestamps for missing rows (limited)
    backfill_missing_timestamps(limit=limit)

    # Derive dates again after new timestamps
    backfill_match_dates_from_timestamps()

    conn = sqlite3.connect(DB_PATH)
    print("After:", counts(conn))
    conn.close()


if __name__ == "__main__":
    main()
