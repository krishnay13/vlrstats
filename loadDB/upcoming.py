"""
Populate next upcoming matches (IDs + projected start time) for VCT 2026 Kickoff events.

- Sources (fixed list):
  - https://www.vlr.gg/event/2682/vct-2026-americas-kickoff
  - https://www.vlr.gg/event/2684/vct-2026-emea-kickoff
  - https://www.vlr.gg/event/2683/vct-2026-pacific-kickoff
  - https://www.vlr.gg/event/2685/vct-2026-china-kickoff

- Behavior:
  - Scrape tournament matches pages to collect candidate match IDs
  - Fetch each match page to parse `match_ts_utc` and teams
  - Keep only future matches (UTC > now)
  - Skip showmatches
  - Upsert into Matches with `match_ts_utc` (and `match_date` as YYYY-MM-DD)
  - Insert team names; if unknown, store "TBD"
  - Limit to 20 soonest matches across all 4 events

Run:
  python -m loadDB.upcoming

This is idempotent: re-running will upsert the same `match_id` rows.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any

import aiohttp
from bs4 import BeautifulSoup

from .db_utils import get_conn, ensure_matches_columns, upsert_match
from .tournament_scraper import scrape_tournament_match_ids, get_tournament_matches_url
from .scrapers.base import fetch_html
from .scrapers.match import extract_match_metadata
from .normalizers.team import normalize_team
from .normalizers.tournament import normalize_tournament

# Fixed list of event URLs provided by user
KICKOFF_2026_EVENTS: List[str] = [
    "https://www.vlr.gg/event/2682/vct-2026-americas-kickoff",
    "https://www.vlr.gg/event/2684/vct-2026-emea-kickoff",
    "https://www.vlr.gg/event/2683/vct-2026-pacific-kickoff",
    "https://www.vlr.gg/event/2685/vct-2026-china-kickoff",
]

# Max candidates to inspect per event to bound HTTP traffic
MAX_CANDIDATES_PER_EVENT = 60
# Overall limit to upsert
UPCOMING_LIMIT = 20
# Concurrency
HTTP_CONCURRENCY = 8


def _parse_iso_utc(ts: str | None) -> datetime | None:
    if not ts:
        return None
    # Handle possible trailing 'Z'
    try:
        if ts.endswith("Z"):
            ts = ts[:-1]
        # fromisoformat expects "+00:00" for tz; treat as UTC naive then localize
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _tbd(name: str | None) -> str:
    if not name:
        return "TBD"
    n = name.strip()
    if not n or n.lower() in {"unknown", "tbd", "pending"}:
        return "TBD"
    return n


async def _fetch_match_meta(session: aiohttp.ClientSession, match_id: int) -> Dict[str, Any] | None:
    """Fetch and parse match metadata for a single match ID."""
    url = f"https://www.vlr.gg/{match_id}"
    try:
        html = await fetch_html(session, url)
        soup = BeautifulSoup(html, "html.parser")
        meta = extract_match_metadata(soup, match_id, url)
        # Normalize entities
        meta["team_a"] = normalize_team(meta.get("team_a") or "")
        meta["team_b"] = normalize_team(meta.get("team_b") or "")
        meta["tournament"] = normalize_tournament(meta.get("tournament") or "")
        return meta
    except Exception:
        return None


async def _collect_event_candidates(session: aiohttp.ClientSession, event_url: str) -> List[int]:
    """Return candidate match IDs for an event (preserves page order)."""
    try:
        # Ensure matches URL resolves (helps some pages)
        _ = await get_tournament_matches_url(event_url)
    except Exception:
        pass  # Fallback to direct scraping anyway
    try:
        ids = await scrape_tournament_match_ids(event_url, completed_only=False)
        return ids[:MAX_CANDIDATES_PER_EVENT]
    except Exception:
        return []


async def collect_upcoming_matches() -> List[Dict[str, Any]]:
    """Collect and return upcoming match meta across configured events."""
    upcoming: List[Dict[str, Any]] = []
    seen: set[int] = set()

    connector = aiohttp.TCPConnector(limit=HTTP_CONCURRENCY)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Gather candidates across events
        all_candidates: List[int] = []
        for ev in KICKOFF_2026_EVENTS:
            cands = await _collect_event_candidates(session, ev)
            for mid in cands:
                if mid not in seen:
                    seen.add(mid)
                    all_candidates.append(mid)

        # Fetch meta concurrently in batches
        sem = asyncio.Semaphore(HTTP_CONCURRENCY)

        async def task(mid: int):
            async with sem:
                return await _fetch_match_meta(session, mid)

        metas: List[Dict[str, Any]] = []
        tasks = [asyncio.create_task(task(mid)) for mid in all_candidates]
        for coro in asyncio.as_completed(tasks):
            m = await coro
            if m:
                metas.append(m)
            # Early exit if we already have enough filtered later? Keep collecting; need time sort.

    # Filter to future and non-showmatch
    now_utc = datetime.now(timezone.utc)
    for m in metas:
        if m.get("is_showmatch"):
            continue
        dt = _parse_iso_utc(m.get("match_ts_utc"))
        if not dt or dt <= now_utc:
            continue
        # Accept as upcoming
        upcoming.append(m)

    # Sort by time asc and take limit
    upcoming.sort(key=lambda x: _parse_iso_utc(x.get("match_ts_utc")) or datetime.max.replace(tzinfo=timezone.utc))
    return upcoming[:UPCOMING_LIMIT]


def upsert_upcoming(rows: List[Dict[str, Any]]) -> int:
    """Upsert upcoming matches into Matches; returns count upserted."""
    if not rows:
        return 0
    conn = get_conn()
    ensure_matches_columns(conn)

    count = 0
    for m in rows:
        match_id = int(m["match_id"]) if m.get("match_id") is not None else None
        if not match_id:
            continue
        tournament = m.get("tournament") or ""
        stage = m.get("stage") or ""
        match_name = m.get("match_name") or f"Match {match_id}"
        team_a = _tbd(m.get("team_a"))
        team_b = _tbd(m.get("team_b"))
        ta_score = m.get("team_a_score")
        tb_score = m.get("team_b_score")
        # For upcoming, treat zero/empty as None to indicate not played
        ta_score = None if (ta_score is None or ta_score == 0) else ta_score
        tb_score = None if (tb_score is None or tb_score == 0) else tb_score
        match_ts_utc = m.get("match_ts_utc")
        match_date = (match_ts_utc or "")[:10] if match_ts_utc else m.get("match_date")
        bans_picks = m.get("bans_picks")
        # Always classify these as VCT
        match_type = "VCT"
        # Result string
        if ta_score is None or tb_score is None:
            match_result = f"{team_a} - {team_b}"
        else:
            match_result = f"{team_a} {ta_score}-{tb_score} {team_b}"

        row = (
            match_id,
            tournament,
            stage,
            match_type,
            match_name,
            team_a,
            team_b,
            ta_score,
            tb_score,
            match_result,
            match_ts_utc,
            match_date,
            bans_picks,
        )
        try:
            upsert_match(conn, row)
            count += 1
        except Exception as e:
            # Continue on individual failures
            print(f"Upsert failed for match {match_id}: {e}")
            continue

    conn.commit()
    conn.close()
    return count


async def main() -> None:
    print("Collecting upcoming matches for VCT 2026 Kickoff events...")
    rows = await collect_upcoming_matches()
    print(f"Found {len(rows)} upcoming matches (pre-limit={UPCOMING_LIMIT})")
    n = upsert_upcoming(rows)
    print(f"Upserted {n} upcoming matches into DB.")


if __name__ == "__main__":
    asyncio.run(main())
