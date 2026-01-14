"""
Validate Matches/Maps/Player_Stats completeness and optionally rescrape bad matches.

Usage examples (from repo root):
  python -m loadDB.validate_and_rescrape --report-only
  python -m loadDB.validate_and_rescrape --fix
"""

import argparse
from typing import List, Dict

from .db_utils import get_conn
from .vlr_ingest import ingest


def find_incomplete_matches() -> Dict[str, List[int]]:
    """
    Scan the database for matches that are missing core data.

    Returns a dict with:
      - 'no_maps': Matches with zero Maps rows
      - 'maps_missing_scores': Maps rows with NULL/empty scores
      - 'no_player_stats': Matches with zero Player_Stats rows
      - 'maps_no_player_stats': Matches with maps but zero Player_Stats rows
    """
    conn = get_conn()
    cur = conn.cursor()

    problems = {
        "no_maps": [],
        "maps_missing_scores": [],
        "no_player_stats": [],
        "maps_no_player_stats": [],
        "bad_match_scores": [],  # e.g. 1–1 series or mismatch vs map wins
    }

    # All match_ids in DB
    cur.execute("SELECT match_id FROM Matches")
    all_match_ids = [row[0] for row in cur.fetchall()]

    for mid in all_match_ids:
        # Maps existence
        cur.execute("SELECT COUNT(*) FROM Maps WHERE match_id = ?", (mid,))
        map_count = cur.fetchone()[0] or 0

        # Player stats existence
        cur.execute("SELECT COUNT(*) FROM Player_Stats WHERE match_id = ?", (mid,))
        ps_count = cur.fetchone()[0] or 0

        # Maps with missing scores
        cur.execute(
            """
            SELECT COUNT(*) 
            FROM Maps 
            WHERE match_id = ? 
              AND (team_a_score IS NULL OR team_b_score IS NULL)
            """,
            (mid,),
        )
        maps_missing_scores = cur.fetchone()[0] or 0

        if map_count == 0:
            problems["no_maps"].append(mid)
        if maps_missing_scores > 0:
            problems["maps_missing_scores"].append(mid)
        if ps_count == 0:
            problems["no_player_stats"].append(mid)
        if map_count > 0 and ps_count == 0:
            problems["maps_no_player_stats"].append(mid)

        # Check for obviously bad match scores:
        #  - series cannot end 1–1 (or any non-zero draw)
        #  - series total rounds can't realistically sum to 1 or 4
        #  - series score should generally equal number of map wins
        cur.execute(
            "SELECT team_a_score, team_b_score FROM Matches WHERE match_id = ?", (mid,)
        )
        row = cur.fetchone()
        if row:
            a_score, b_score = row
            # Treat NULL as 0 for this check
            a_score = a_score or 0
            b_score = b_score or 0

            # Flag 1–1 (or any non-zero draw) as bad at the match/series level
            if a_score == b_score and a_score > 0:
                problems["bad_match_scores"].append(mid)

            # Compare against map wins if we have maps with scores
            if map_count > 0:
                cur.execute(
                    """
                    SELECT team_a_score, team_b_score
                    FROM Maps
                    WHERE match_id = ?
                      AND team_a_score IS NOT NULL
                      AND team_b_score IS NOT NULL
                    """,
                    (mid,),
                )
                map_rows = cur.fetchall()
                if map_rows:
                    # Check for impossible map-level scores (e.g. very low totals like 1 or 4, or 1–1)
                    bad_map_score = False
                    for ta, tb in map_rows:
                        ta = ta or 0
                        tb = tb or 0
                        total = ta + tb
                        if (ta == tb and ta > 0) or total in (1, 4):
                            bad_map_score = True
                            break

                    if bad_map_score:
                        problems["bad_match_scores"].append(mid)
                    else:
                        # Only compare aggregate series score vs map wins if individual maps look sane
                        a_wins = sum(1 for ta, tb in map_rows if (ta or 0) > (tb or 0))
                        b_wins = sum(1 for ta, tb in map_rows if (tb or 0) > (ta or 0))
                        if a_wins + b_wins >= 2:
                            if a_wins != a_score or b_wins != b_score:
                                problems["bad_match_scores"].append(mid)

    conn.close()
    return problems


def print_report(problems: Dict[str, List[int]]) -> None:
    """Pretty-print a summary of incomplete matches."""
    total_bad = set(
        problems["no_maps"]
        + problems["maps_missing_scores"]
        + problems["no_player_stats"]
        + problems["maps_no_player_stats"]
    )

    print("=" * 70)
    print("MATCH COMPLETENESS REPORT")
    print("=" * 70)
    print(f"Total matches with any issue: {len(total_bad)}")
    print(f"  - No maps: {len(problems['no_maps'])}")
    print(f"  - Maps with NULL scores: {len(problems['maps_missing_scores'])}")
    print(f"  - No player stats: {len(problems['no_player_stats'])}")
    print(f"  - Maps but no player stats: {len(problems['maps_no_player_stats'])}")
    print(f"  - Bad match scores (draws/mismatches): {len(problems['bad_match_scores'])}")
    print()

    def preview(label: str, ids: List[int], limit: int = 15):
        if not ids:
            return
        print(f"{label} (showing up to {limit}):")
        print("  " + ", ".join(str(i) for i in ids[:limit]))
        if len(ids) > limit:
            print(f"  ... and {len(ids) - limit} more")
        print()

    preview("No maps", problems["no_maps"])
    preview("Maps with NULL scores", problems["maps_missing_scores"])
    preview("No player stats", problems["no_player_stats"])
    preview("Maps but no player stats", problems["maps_no_player_stats"])
    preview("Bad match scores", problems["bad_match_scores"])


def rescrape_matches(match_ids: List[int], batch_size: int = 25) -> None:
    """
    Rescrape a list of match_ids using the existing ingest() pipeline.

    This will re-fetch each match page and upsert Maps + Player_Stats.
    """
    if not match_ids:
        print("No matches to rescrape.")
        return

    print("=" * 70)
    print(f"RESCRAPING {len(match_ids)} MATCHES")
    print("=" * 70)

    total_batches = (len(match_ids) + batch_size - 1) // batch_size
    for i in range(0, len(match_ids), batch_size):
        batch = match_ids[i : i + batch_size]
        batch_num = i // batch_size + 1
        print(f"  Batch {batch_num}/{total_batches}: {len(batch)} matches -> {batch}")
        try:
            # match_type=None so vlr_ingest auto-detects VCT / SHOWMATCH
            ingest(batch, match_type=None)
            print("    [OK] Ingested batch")
        except Exception as e:
            print(f"    [ERROR] Failed to ingest batch: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Validate match completeness and optionally rescrape incomplete matches."
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Rescrape all matches with missing maps/scores/player stats.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit on number of bad matches to rescrape (0 = no limit).",
    )
    args = parser.parse_args()

    problems = find_incomplete_matches()
    print_report(problems)

    if not args.fix:
        print("Run again with --fix to rescrape incomplete matches.")
        return

    # Union of all problematic match_ids
    all_bad = list(
        sorted(
            set(
                problems["no_maps"]
                + problems["maps_missing_scores"]
                + problems["no_player_stats"]
                + problems["maps_no_player_stats"]
                + problems["bad_match_scores"]
            )
        )
    )

    if args.limit > 0:
        all_bad = all_bad[: args.limit]

    if not all_bad:
        print("No incomplete matches found. Nothing to fix.")
        return

    rescrape_matches(all_bad)


if __name__ == "__main__":
    main()

