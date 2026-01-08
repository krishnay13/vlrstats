import sqlite3
from .db_utils import get_conn, ensure_matches_columns
from .vlr_ingest import scrape_match
import asyncio


def backfill_missing_timestamps(limit: int = 100):
    conn = get_conn()
    ensure_matches_columns(conn)
    cur = conn.cursor()
    cur.execute("SELECT match_id FROM Matches WHERE match_ts_utc IS NULL ORDER BY match_id ASC LIMIT ?", (limit,))
    ids = [row[0] for row in cur.fetchall()]
    if not ids:
        print("No matches missing timestamps.")
        conn.close()
        return

    async def run(ids_):
        for mid in ids_:
            match_row, maps_info, players_info = await scrape_match(mid)
            # only update timestamp for safety
            cur2 = conn.cursor()
            # match_row structure ends with (match_ts_utc, match_date)
            ts_utc = match_row[-2]
            cur2.execute(
                "UPDATE Matches SET match_ts_utc = ? WHERE match_id = ? AND match_ts_utc IS NULL",
                (ts_utc, mid),
            )
            conn.commit()

    asyncio.run(run(ids))
    conn.close()


def backfill_match_dates_from_timestamps():
    """Populate Matches.match_date from Matches.match_ts_utc when missing."""
    conn = get_conn()
    ensure_matches_columns(conn)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE Matches
        SET match_date = substr(match_ts_utc, 1, 10)
        WHERE match_ts_utc IS NOT NULL AND (match_date IS NULL OR match_date = '')
        """
    )
    conn.commit()
    conn.close()
