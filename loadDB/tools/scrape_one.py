import argparse
import sqlite3
import sys
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import Optional

from loadDB.config import DB_PATH
from loadDB.vlr_ingest import scrape_match, fetch_html


def get_one_missing_match_id(conn: sqlite3.Connection) -> Optional[int]:
    """
    Get a match ID that is missing timestamp data.
    
    Prefers recent match IDs (ordered by match_id DESC).
    
    Args:
        conn: Database connection
    
    Returns:
        Match ID if found, None otherwise
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT match_id FROM matches WHERE match_ts_utc IS NULL ORDER BY match_id DESC LIMIT 1"
    )
    row = cur.fetchone()
    return int(row[0]) if row else None


def update_match_ts_date(conn: sqlite3.Connection, match_id: int, ts: Optional[str], date: Optional[str]) -> None:
    """
    Update match timestamp and date in database.
    
    Args:
        conn: Database connection
        match_id: Match ID to update
        ts: UTC timestamp string
        date: Date string
    """
    cur = conn.cursor()
    cur.execute(
        "UPDATE matches SET match_ts_utc = ?, match_date = ? WHERE match_id = ?",
        (ts, date, match_id),
    )
    conn.commit()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Scrape a single VLR match to verify timestamp/date parsing.")
    parser.add_argument("--match-id", type=int, help="Specific match_id to scrape; defaults to one missing ts/date")
    parser.add_argument("--update", action="store_true", help="If set, update the DB with scraped ts/date")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    try:
        match_id: Optional[int] = args.match_id
        if match_id is None:
            match_id = get_one_missing_match_id(conn)
            if match_id is None:
                print("No matches with missing timestamps found.")
                return 0

        print(f"Scraping match_id={match_id}...")
        url = f"https://www.vlr.gg/{match_id}"
        async def _fetch():
            async with aiohttp.ClientSession() as session:
                return await fetch_html(session, url)
        html = asyncio.run(_fetch())
        print(f"Fetched HTML length={len(html)} markers: vm-stats-game?={'vm-stats-game' in html} data-utc-ts?={'data-utc-ts' in html}")
        soup = BeautifulSoup(html, 'html.parser')
        ts_nodes = soup.select('[data-utc-ts]')
        sample_ts = []
        for el in ts_nodes[:5]:
            sample_ts.append(el.get('data-utc-ts'))
        print(f"Found {len(ts_nodes)} elements with data-utc-ts. Samples={sample_ts}")
        match_row, maps, players = asyncio.run(scrape_match(match_id))

        # Convention: match_row[-2] = match_ts_utc, match_row[-1] = match_date
        ts_utc = match_row[-2] if len(match_row) >= 2 else None
        match_date = match_row[-1] if len(match_row) >= 1 else None

        print(f"Result: match_ts_utc={ts_utc} match_date={match_date}")
        print(f"Maps parsed={len(maps)} Players parsed={len(players)}")

        if args.update:
            update_match_ts_date(conn, match_id, ts_utc, match_date)
            print("DB updated for this match.")

        return 0
    except Exception as e:
        print(f"Error scraping match: {e}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
