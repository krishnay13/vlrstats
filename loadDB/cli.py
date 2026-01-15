import argparse
import asyncio
from . import vlr_ingest
from .elo import compute_elo
from .display import top_players, top_teams, team_history, player_history
from .tournament_scraper import scrape_tournament_match_ids, save_match_ids_to_file, load_match_ids_from_file


def main():
    parser = argparse.ArgumentParser(prog="vlr", description="VLR Stats CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ingest = sub.add_parser("ingest", help="Ingest matches by ID or URL")
    p_ingest.add_argument("items", nargs="+", help="Match IDs or URLs")

    p_elo = sub.add_parser("elo", help="Compute Elo ratings")
    p_elo.add_argument("action", choices=["compute"], help="Elo action")
    p_elo.add_argument("--save", action="store_true", help="Persist history and snapshots")
    p_elo.add_argument("--top", type=int, default=20, help="Print top N teams after compute")
    p_elo.add_argument(
        "--recency-half-life",
        type=float,
        default=None,
        help="Optional half-life in matches for recency weighting (larger = slower decay, omit to disable)",
    )
    p_elo.add_argument(
        "--delta-summary",
        action="store_true",
        help="Print summary statistics of Elo rating deltas (per team per match)",
    )

    p_show = sub.add_parser("show", help="Display current snapshots or histories")
    p_show_sub = p_show.add_subparsers(dest="show_cmd", required=True)
    p_topteams = p_show_sub.add_parser("top-teams", help="Show top teams")
    p_topteams.add_argument("-n", type=int, default=20, help="Number of teams to show")
    p_topteams.add_argument("--date-range", type=str, help="Date range: 2024, 2025, last-3-months, last-6-months, or all-time (default)")
    p_topplayers = p_show_sub.add_parser("top-players", help="Show top players")
    p_topplayers.add_argument("-n", type=int, default=20)
    p_t_history = p_show_sub.add_parser("team-history", help="Show team Elo history")
    p_t_history.add_argument("team")
    p_p_history = p_show_sub.add_parser("player-history", help="Show player Elo history")
    p_p_history.add_argument("player")

    p_scrape_tournament = sub.add_parser("scrape-tournament", help="Scrape match IDs from a tournament")
    p_scrape_tournament.add_argument("url", help="Tournament event URL (e.g., https://www.vlr.gg/event/2792)")
    p_scrape_tournament.add_argument("-o", "--output", help="Output file path (default: tournament_matches.txt)", default="tournament_matches.txt")
    p_scrape_tournament.add_argument("--all", action="store_true", help="Include all matches, not just completed ones")

    p_ingest_tournament = sub.add_parser("ingest-tournament", help="Scrape match IDs from a tournament and ingest them into the database")
    p_ingest_tournament.add_argument("url", help="Tournament event URL (e.g., https://www.vlr.gg/event/2792)")
    p_ingest_tournament.add_argument("--match-type", required=True, choices=["VCT", "VCL", "OFFSEASON"], help="Match type (VCT, VCL, or OFFSEASON)")
    p_ingest_tournament.add_argument("-o", "--output", help="Output file path for match IDs (default: tournament_matches.txt)", default="tournament_matches.txt")
    p_ingest_tournament.add_argument("--all", action="store_true", help="Include all matches, not just completed ones")
    p_ingest_tournament.add_argument("--no-ingest", action="store_true", help="Only scrape and save to file, don't ingest (for manual review)")

    p_upload_file = sub.add_parser("upload-from-file", help="Upload matches from a file")
    p_upload_file.add_argument("file", help="File containing match IDs (one per line)")
    p_upload_file.add_argument("--match-type", choices=["VCL", "OFFSEASON", "VCT"], help="Match type (VCL, OFFSEASON, or VCT). Note: Showmatches are automatically skipped.")

    p_ingest_file = sub.add_parser("ingest-from-file", help="Ingest matches from a file containing URLs (one per line)")
    p_ingest_file.add_argument("file", help="File containing match URLs (one per line). Supports per-line match type: URL # VCT")
    p_ingest_file.add_argument("--match-type", choices=["VCL", "OFFSEASON", "VCT"], help="Global match type override for all URLs (otherwise auto-detected or use per-line comments)")
    p_ingest_file.add_argument("--no-validate", action="store_true", help="Skip data validation")

    p_remove_showmatches = sub.add_parser("remove-showmatches", help="Remove all showmatch data from the database")
    p_remove_showmatches.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")

    p_scrape_all_vct = sub.add_parser("scrape-all-vct", help="Clear DB and scrape all VCT 2024 & 2025 matches")

    p_audit_vct = sub.add_parser("audit-vct", help="Audit and optionally backfill key VCT 2024/2025 events")
    p_audit_vct.add_argument("--ingest-missing", action="store_true", help="Ingest any missing matches for each event")
    p_audit_vct.add_argument("--no-validate", action="store_true", help="Skip data validation during ingestion")

    p_rescrape_empty_stage = sub.add_parser("rescrape-empty-stage", help="Rescrape matches with empty stage fields (e.g., misparsed tournaments like 'NRG vs. Cloud9')")
    p_rescrape_empty_stage.add_argument("--limit", type=int, default=None, help="Optional limit on number of matches to rescrape")

    p_rescrape_bad_meta = sub.add_parser(
        "rescrape-bad-metadata",
        help="Rescrape VCT matches with generic/empty tournament names and refresh their metadata/maps/player stats",
    )
    p_rescrape_bad_meta.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of matches to rescrape",
    )
    p_rescrape_bad_meta.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip data validation during rescrape",
    )

    p_test_matches = sub.add_parser("test-matches", help="Test random matches for data quality")
    p_test_matches.add_argument("-n", "--num", type=int, default=10, help="Number of random matches to test")

    p_standardize = sub.add_parser("standardize-teams", help="Use LLM or heuristics to standardize team names and identify duplicates")
    p_standardize.add_argument("--provider", choices=["openai", "anthropic", "heuristics"], default="openai", help="Provider: LLM (openai/anthropic) or heuristics (default: openai)")
    p_standardize.add_argument("--api-key", type=str, help="API key (or set OPENAI_API_KEY/ANTHROPIC_API_KEY env var)")
    p_standardize.add_argument("--preview", action="store_true", help="Preview mappings without saving")
    p_standardize.add_argument("--no-save", action="store_true", help="Don't save to aliases.json")
    p_standardize.add_argument("--fallback", action="store_true", help="Fall back to heuristics if LLM fails")

    args = parser.parse_args()

    if args.cmd == "ingest":
        # Cast numeric-looking items to int for convenience
        items = [int(x) if str(x).isdigit() else x for x in args.items]
        vlr_ingest.ingest(items)
        return

    if args.cmd == "elo" and args.action == "compute":
        compute_elo(
            save=args.save,
            top=args.top,
            recency_half_life=getattr(args, "recency_half_life", None),
            delta_summary=getattr(args, "delta_summary", False),
        )
        return

    if args.cmd == "show":
        if args.show_cmd == "top-teams":
            date_range = getattr(args, 'date_range', None)
            teams = top_teams(args.n, date_range=date_range)
            date_display = f" ({date_range})" if date_range and date_range != "all-time" else ""
            print(f"Top {len(teams)} Teams by Elo{date_display}:")
            for i, (team, rating, matches) in enumerate(teams, 1):
                print(f"{i:2d}. {team:30s} {rating:7.2f} ({matches} matches)")
        elif args.show_cmd == "top-players":
            for i, (player, team, rating, matches) in enumerate(top_players(args.n), 1):
                team_disp = team or ""
                print(f"{i:2d}. {player:24s} {rating:7.2f} ({matches} matches) {team_disp}")
        elif args.show_cmd == "team-history":
            rows = team_history(args.team)
            for (mid, tournament, stage, match_type, opp, pre, post) in rows:
                delta = post - pre
                context = f"{tournament} | {stage} | {match_type}" if tournament or stage or match_type else ""
                print(f"#{mid} {context} vs {opp}: {pre:.2f} -> {post:.2f} (Δ {delta:+.2f})")
        elif args.show_cmd == "player-history":
            rows = player_history(args.player)
            for (mid, team, opp_team, pre, post) in rows:
                delta = post - pre
                print(f"#{mid} {team or ''} vs {opp_team or ''}: {pre:.2f} -> {post:.2f} (Δ {delta:+.2f})")

    if args.cmd == "scrape-tournament":
        print(f"Scraping match IDs from tournament: {args.url}")
        print(f"Completed only: {not args.all}")
        try:
            match_ids = asyncio.run(scrape_tournament_match_ids(args.url, completed_only=not args.all))
            if match_ids:
                save_match_ids_to_file(match_ids, args.output)
                print(f"Found {len(match_ids)} match(es). Saved to {args.output}")
                print(f"Match IDs: {', '.join(map(str, match_ids))}")
            else:
                print("No matches found.")
        except Exception as e:
            print(f"Error scraping tournament: {e}")
            return 1

    if args.cmd == "ingest-tournament":
        from .ingestion import ingest_from_urls
        
        print(f"Scraping match IDs from tournament: {args.url}")
        print(f"Match type: {args.match_type}")
        print(f"Completed only: {not args.all}")
        
        try:
            # Step 1: Scrape match IDs
            match_ids = asyncio.run(scrape_tournament_match_ids(args.url, completed_only=not args.all))
            
            if not match_ids:
                print("No matches found.")
                return 1
            
            print(f"Found {len(match_ids)} match(es)")
            
            # Step 2: Save to txt file
            save_match_ids_to_file(match_ids, args.output)
            print(f"Match IDs saved to {args.output}")
            
            # Step 3: Convert match IDs to URLs and ingest (unless --no-ingest flag is set)
            if not args.no_ingest:
                urls = [f"https://www.vlr.gg/{match_id}" for match_id in match_ids]
                print(f"Starting ingestion of {len(urls)} match(es) (this may take a while)...")
                
                result = asyncio.run(ingest_from_urls(
                    urls,
                    validate=True,
                    match_type=args.match_type
                ))
                
                print(f"\nIngestion complete:")
                print(f"  Success: {result.success_count}")
                print(f"  Errors: {result.error_count}")
                if result.skipped_count > 0:
                    print(f"  Skipped (showmatches): {result.skipped_count}")
                if result.warnings:
                    print(f"  Warnings: {len(result.warnings)}")
                    for warning in result.warnings[:5]:  # Show first 5 warnings
                        print(f"    - {warning}")
                    if len(result.warnings) > 5:
                        print(f"    ... and {len(result.warnings) - 5} more warnings")
                if result.errors:
                    print(f"  Error details:")
                    for error in result.errors[:5]:  # Show first 5 errors
                        print(f"    - {error}")
                    if len(result.errors) > 5:
                        print(f"    ... and {len(result.errors) - 5} more errors")
                
                if result.error_count > 0:
                    return 1
            else:
                print(f"Skipping ingestion (--no-ingest flag set)")
                print(f"Match IDs saved to {args.output} for manual review")
                print(f"To ingest later, use: python -m loadDB.cli upload-from-file {args.output} --match-type {args.match_type}")
                
        except Exception as e:
            print(f"Error processing tournament: {e}")
            import traceback
            traceback.print_exc()
            return 1

    if args.cmd == "upload-from-file":
        match_ids = load_match_ids_from_file(args.file)
        if not match_ids:
            print(f"No match IDs found in {args.file}")
            return 1
        
        print(f"Found {len(match_ids)} match ID(s) in {args.file}")
        
        # Get match type from user if not provided
        match_type = args.match_type
        if not match_type:
            while True:
                user_input = input("Enter match type (VCL, OFFSEASON, or VCT): ").strip().upper()
                if user_input in ["VCL", "OFFSEASON", "VCT"]:
                    match_type = user_input
                    break
                else:
                    print("Invalid input. Please enter VCL, OFFSEASON, or VCT.")
        
        print(f"Uploading {len(match_ids)} match(es) with match type: {match_type}")
        try:
            vlr_ingest.ingest(match_ids, match_type=match_type)
            print(f"Successfully uploaded {len(match_ids)} match(es)")
        except Exception as e:
            print(f"Error uploading matches: {e}")
            return 1

    if args.cmd == "ingest-from-file":
        from .ingestion import load_urls_from_file, ingest_from_urls
        try:
            urls = load_urls_from_file(args.file)
            if not urls:
                print(f"No URLs found in {args.file}")
                return 1
            
            print(f"Found {len(urls)} URL(s) in {args.file}")
            print("Starting ingestion (this may take a while)...")
            
            result = asyncio.run(ingest_from_urls(
                urls,
                validate=not args.no_validate,
                match_type=args.match_type
            ))
            
            print(f"\nIngestion complete:")
            print(f"  Success: {result.success_count}")
            print(f"  Errors: {result.error_count}")
            if result.skipped_count > 0:
                print(f"  Skipped (showmatches): {result.skipped_count}")
            if result.warnings:
                print(f"  Warnings: {len(result.warnings)}")
                for warning in result.warnings[:5]:  # Show first 5 warnings
                    print(f"    - {warning}")
                if len(result.warnings) > 5:
                    print(f"    ... and {len(result.warnings) - 5} more warnings")
            if result.errors:
                print(f"  Error details:")
                for error in result.errors[:5]:  # Show first 5 errors
                    print(f"    - {error}")
                if len(result.errors) > 5:
                    print(f"    ... and {len(result.errors) - 5} more errors")
        except Exception as e:
            print(f"Error ingesting from file: {e}")
            import traceback
            traceback.print_exc()
            return 1

    if args.cmd == "scrape-all-vct":
        from .scrape_all_vct import main as scrape_main
        asyncio.run(scrape_main())
        return

    if args.cmd == "rescrape-bad-metadata":
        from .db_utils import get_conn
        from .ingestion import ingest_from_urls

        conn = get_conn()
        cur = conn.cursor()

        # Find VCT matches with clearly bad/suspicious metadata.
        # Heuristics:
        # - match_type is VCT (or empty/unknown)
        # - AND at least ONE of:
        #     * tournament is generic/flattened or empty (e.g. 'VCT 2024', 'VCT 2025', '')
        #     * stage is empty/NULL
        #     * match_name looks like a tournament (starts with 'VCT ' or 'Champions Tour ')
        #       or exactly equals the tournament name (tournament accidentally stored as match_name)
        cur.execute(
            """
            SELECT match_id
            FROM Matches
            WHERE (match_type = 'VCT' OR TRIM(IFNULL(match_type, '')) = '')
              AND (
                    TRIM(IFNULL(tournament, '')) IN ('VCT 2024', 'VCT 2025', '')
                 OR stage IS NULL
                 OR TRIM(stage) = ''
                 OR UPPER(TRIM(IFNULL(match_name, ''))) = UPPER(TRIM(IFNULL(tournament, '')))
                 OR UPPER(TRIM(IFNULL(match_name, ''))) LIKE 'VCT 20__%'
                 OR UPPER(TRIM(IFNULL(match_name, ''))) LIKE 'CHAMPIONS TOUR 20__%'
              )
            ORDER BY match_id
            """
        )
        rows = cur.fetchall()
        conn.close()

        match_ids = [row[0] for row in rows]
        total_found = len(match_ids)

        if args.limit is not None:
            match_ids = match_ids[: args.limit]

        if not match_ids:
            print("No VCT matches with generic/empty tournament metadata found.")
            return 0

        print(
            f"Found {total_found} VCT match(es) with generic/empty tournament names; "
            f"rescraping {len(match_ids)} of them..."
        )

        urls = [f"https://www.vlr.gg/{mid}" for mid in match_ids]

        try:
            result = asyncio.run(
                ingest_from_urls(
                    urls,
                    validate=not args.no_validate,
                    match_type="VCT",
                )
            )
        except Exception as e:
            print(f"Error rescraping bad-metadata matches: {e}")
            import traceback
            traceback.print_exc()
            return 1

        print("\nRescrape (bad metadata) complete:")
        print(f"  Success: {result.success_count}")
        print(f"  Errors: {result.error_count}")
        if result.skipped_count > 0:
            print(f"  Skipped (showmatches): {result.skipped_count}")
        if result.warnings:
            print(f"  Warnings: {len(result.warnings)}")
            for warning in result.warnings[:5]:
                print(f"    - {warning}")
            if len(result.warnings) > 5:
                print(f"    ... and {len(result.warnings) - 5} more warnings")
        if result.errors:
            print(f"  Error details:")
            for error in result.errors[:5]:
                print(f"    - {error}")
            if len(result.errors) > 5:
                print(f"    ... and {len(result.errors) - 5} more errors")

        return 0

    if args.cmd == "rescrape-empty-stage":
        from .db_utils import get_conn
        from .ingestion import ingest_from_urls

        conn = get_conn()
        cur = conn.cursor()

        # Find matches with empty or NULL stage, restricted to VCT matches
        cur.execute(
            """
            SELECT match_id
            FROM Matches
            WHERE (stage IS NULL OR TRIM(stage) = '')
              AND (match_type = 'VCT' OR match_type IS NULL OR TRIM(match_type) = '')
            ORDER BY match_id
            """
        )
        rows = cur.fetchall()
        conn.close()

        match_ids = [row[0] for row in rows]
        if args.limit is not None:
            match_ids = match_ids[: args.limit]

        if not match_ids:
            print("No matches with empty stage found (for VCT/unknown types).")
            return 0

        print(f"Found {len(rows)} matches with empty stage; rescraping {len(match_ids)} of them...")

        urls = [f"https://www.vlr.gg/{mid}" for mid in match_ids]

        try:
            result = asyncio.run(
                ingest_from_urls(
                    urls,
                    validate=True,
                    match_type="VCT",
                )
            )
        except Exception as e:
            print(f"Error rescraping matches: {e}")
            import traceback
            traceback.print_exc()
            return 1

        print("\nRescrape complete:")
        print(f"  Success: {result.success_count}")
        print(f"  Errors: {result.error_count}")
        if result.skipped_count > 0:
            print(f"  Skipped (showmatches): {result.skipped_count}")
        if result.warnings:
            print(f"  Warnings: {len(result.warnings)}")
            for warning in result.warnings[:5]:
                print(f"    - {warning}")
            if len(result.warnings) > 5:
                print(f"    ... and {len(result.warnings) - 5} more warnings")
        if result.errors:
            print(f"  Error details:")
            for error in result.errors[:5]:
                print(f"    - {error}")
            if len(result.errors) > 5:
                print(f"    ... and {len(result.errors) - 5} more errors")

        return 0

    if args.cmd == "audit-vct":
        from .vct_scraper import get_vct_target_events
        from .tournament_scraper import scrape_tournament_match_ids
        from .db_utils import get_conn
        from .ingestion import ingest_from_urls

        print("Enumerating VCT 2024/2025 target events...")
        events = asyncio.run(get_vct_target_events())
        if not events:
            print("No VCT events found to audit.")
            return 1

        print(f"Found {len(events)} target events:\n")
        for e in events:
            exp = e.get("expected_matches")
            show = e.get("expected_showmatches")
            exp_str = "unknown"
            if exp is not None:
                if show:
                    exp_str = f"{exp} total ({exp - show} after removing {show} showmatch(es))"
                else:
                    exp_str = f"{exp} (no showmatches expected)"
            print(f"- {e['year']} {e['phase'].upper()} {e['region'].upper()}: {e['name']}")
            print(f"  URL: {e['url']}")
            print(f"  Expected matches: {exp_str}\n")

        conn = get_conn()
        cur = conn.cursor()

        total_missing = 0
        total_ingested_success = 0
        total_ingested_errors = 0

        for e in events:
            print("\n" + "=" * 70)
            print(f"Auditing {e['year']} {e['phase'].upper()} {e['region'].upper()}: {e['name']}")
            print("=" * 70)

            try:
                ids_completed = asyncio.run(
                    scrape_tournament_match_ids(e["url"], completed_only=True)
                )
                ids_all = asyncio.run(
                    scrape_tournament_match_ids(e["url"], completed_only=False)
                )
            except Exception as ex:
                print(f"Error scraping tournament {e['url']}: {ex}")
                import traceback
                traceback.print_exc()
                continue

            set_completed = set(ids_completed)
            # Preserve order for truth_ids but ensure uniqueness
            seen = set()
            truth_ids: list[int] = []
            for mid in ids_all:
                if mid not in seen:
                    seen.add(mid)
                    truth_ids.append(mid)

            print(f"  VLR IDs (completed_only=True): {len(ids_completed)}")
            print(f"  VLR IDs (all matches)      : {len(truth_ids)}")
            print(f"  Extra IDs only in 'all'    : {len(set(truth_ids) - set_completed)}")

            exp = e.get("expected_matches")
            show = e.get("expected_showmatches")
            if exp is not None:
                if len(truth_ids) != exp:
                    print(
                        f"  WARNING: Expected {exp} total matches for this event, "
                        f"but scraped {len(truth_ids)} from VLR."
                    )
                else:
                    print("  Scraped match count matches expected total.")

            if not truth_ids:
                print("  No VLR match IDs found for this event; skipping DB comparison.")
                continue

            # Compare with DB contents using match_id membership, which is robust across tournament name variants
            placeholders = ",".join("?" * len(truth_ids))
            cur.execute(
                f"SELECT match_id FROM Matches WHERE match_id IN ({placeholders})",
                truth_ids,
            )
            db_ids = {row[0] for row in cur.fetchall()}

            missing_ids = [mid for mid in truth_ids if mid not in db_ids]
            extra_ids = [mid for mid in db_ids if mid not in set(truth_ids)]

            print(f"  Matches already in DB      : {len(db_ids)}")
            print(f"  Missing matches (in VLR)   : {len(missing_ids)}")
            if extra_ids:
                print(f"  Extra DB matches not in VLR list: {len(extra_ids)}")

            if missing_ids:
                total_missing += len(missing_ids)
                print("  Missing match IDs (first 15):")
                print("   ", ", ".join(str(m) for m in missing_ids[:15]))
                if len(missing_ids) > 15:
                    print(f"    ... and {len(missing_ids) - 15} more")

                if args.ingest_missing:
                    urls = [f"https://www.vlr.gg/{mid}" for mid in missing_ids]
                    print(f"\n  Ingesting {len(urls)} missing match(es) as VCT...")
                    try:
                        result = asyncio.run(
                            ingest_from_urls(
                                urls,
                                validate=not args.no_validate,
                                match_type="VCT",
                            )
                        )
                        print(f"    Success: {result.success_count}")
                        print(f"    Errors : {result.error_count}")
                        if result.skipped_count:
                            print(f"    Skipped (showmatches): {result.skipped_count}")
                        total_ingested_success += result.success_count
                        total_ingested_errors += result.error_count
                    except Exception as ex:
                        print(f"    ERROR ingesting missing matches: {ex}")
                        import traceback
                        traceback.print_exc()
            else:
                print("  No missing matches for this event.")

        conn.close()

        print("\n" + "=" * 70)
        print("VCT 2024/2025 audit summary")
        print("=" * 70)
        print(f"Total missing matches across all events (before ingest): {total_missing}")
        if args.ingest_missing:
            print(f"Total ingested successfully: {total_ingested_success}")
            print(f"Total ingestion errors     : {total_ingested_errors}")
        else:
            print("No ingestion performed (run again with --ingest-missing to backfill).")

        return 0

    if args.cmd == "test-matches":
        from .test_matches import test_random_matches
        test_random_matches(args.num)
        return

    if args.cmd == "standardize-teams":
        from .team_standardizer import standardize_teams, get_all_team_names, standardize_with_heuristics
        try:
            if args.preview:
                team_names = get_all_team_names()
                print(f"Found {len(team_names)} unique team names\n")
                if args.provider == "heuristics":
                    new_mappings = standardize_with_heuristics(team_names)
                elif args.provider == "openai":
                    from .team_standardizer import standardize_with_llm
                    new_mappings = standardize_with_llm(team_names, args.api_key)
                else:
                    from .team_standardizer import standardize_with_anthropic
                    new_mappings = standardize_with_anthropic(team_names, args.api_key)
                print("\n" + "=" * 70)
                print("PREVIEW - New mappings (not saved):")
                print("=" * 70)
                for variant, canonical in sorted(new_mappings.items()):
                    print(f"  {variant:50s} -> {canonical}")
            else:
                standardize_teams(
                    provider=args.provider,
                    api_key=args.api_key,
                    save=not args.no_save,
                    use_heuristics=args.fallback
                )
        except ImportError as e:
            print(f"Error: {e}")
            print("\nPlease install required package:")
            if "openai" in str(e):
                print("  pip install openai")
            elif "anthropic" in str(e):
                print("  pip install anthropic")
        except Exception as e:
            print(f"Error standardizing teams: {e}")
            import traceback
            traceback.print_exc()
            return 1
        return

    if args.cmd == "remove-showmatches":
        from .db_utils import get_conn
        from .normalizers.team import normalize_team
        import sqlite3
        import re
        
        def is_showmatch_team(team_name: str) -> bool:
            """Check if a team name is a showmatch team (Python equivalent of frontend logic)."""
            if not team_name:
                return False
            
            name = team_name.lower().strip()
            
            # Known showmatch teams
            showmatch_teams = [
                'team international', 'team spain', 'team china', 'team tarik',
                'team thailand', 'team world', 'glory once again', 'team emea',
                'team france', 'team toast', 'team alpha', 'team omega',
                'pure aim', 'precise defeat',
                # Additional showmatch teams from database scan
                'alp', 'cjmz', 'cn', 'emea', 'eq118', 'fra', 'goa', 'hs',
                'intl', 'ome', 'team', 'wor', 'thai',
                # Player names stored as teams (showmatch issues)
                'dank1ng', 'dohyeon', 'fugu', 'heart bus', 'jisou', 'karsaj',
                'sergioferra', 'spicyuuu', 'tarik', 'xiaojue', 'yjj', 'zhang yanqi',
            ]
            
            # Check exact matches
            if name in showmatch_teams:
                return True
            
            # Check for "team " prefix with showmatch indicators
            if 'team ' in name and any(indicator in name for indicator in [
                'showmatch', 'all-star', 'international', 'spain', 'china',
                'tarik', 'thailand', 'world', 'emea', 'france', 'toast',
                'alpha', 'omega'
            ]):
                return True
            
            # Check for "glory once again"
            if 'glory once again' in name:
                return True
            
            return False
        
        conn = get_conn()
        cur = conn.cursor()
        
        # Comprehensive showmatch detection
        # 1. Find matches where match_type = 'SHOWMATCH'
        cur.execute("SELECT match_id FROM Matches WHERE match_type = 'SHOWMATCH'")
        match_ids_by_type = {row[0] for row in cur.fetchall()}
        
        # 2. Find matches with showmatch teams
        cur.execute("SELECT match_id, team_a, team_b FROM Matches")
        all_matches = cur.fetchall()
        match_ids_by_teams = set()
        
        for match_id, team_a, team_b in all_matches:
            # Normalize team names
            team_a_norm = normalize_team(team_a) if team_a else ""
            team_b_norm = normalize_team(team_b) if team_b else ""
            
            if is_showmatch_team(team_a_norm) or is_showmatch_team(team_b_norm):
                match_ids_by_teams.add(match_id)
        
        # 3. Find matches where tournament/stage/match_name contains "showmatch" (case-insensitive)
        cur.execute("SELECT match_id, tournament, stage, match_name FROM Matches")
        match_ids_by_name = set()
        
        for match_id, tournament, stage, match_name in cur.fetchall():
            tournament_lower = (tournament or '').lower()
            stage_lower = (stage or '').lower()
            match_name_lower = (match_name or '').lower()
            
            if any('showmatch' in text or 'all-star' in text for text in [tournament_lower, stage_lower, match_name_lower]):
                match_ids_by_name.add(match_id)
        
        # Combine all match IDs
        all_match_ids = match_ids_by_type | match_ids_by_teams | match_ids_by_name
        
        if not all_match_ids:
            print("No showmatches found in database.")
            conn.close()
            return 0
        
        print(f"Found {len(all_match_ids)} showmatch match(es) to delete:")
        print(f"  - {len(match_ids_by_type)} by match_type = 'SHOWMATCH'")
        print(f"  - {len(match_ids_by_teams)} by showmatch teams")
        print(f"  - {len(match_ids_by_name)} by tournament/stage/match_name containing 'showmatch'")
        
        if args.dry_run:
            print(f"\nDRY RUN: Would delete {len(all_match_ids)} showmatch(es)")
            # Show sample matches
            sample_ids = list(all_match_ids)[:10]
            placeholders = ','.join('?' * len(sample_ids))
            cur.execute(
                f"SELECT match_id, team_a, team_b, match_name, tournament, stage FROM Matches WHERE match_id IN ({placeholders})",
                sample_ids
            )
            matches = cur.fetchall()
            print("\nSample matches that would be deleted:")
            for match_id, team_a, team_b, match_name, tournament, stage in matches:
                print(f"  Match {match_id}: {team_a} vs {team_b}")
                print(f"    Tournament: {tournament}, Stage: {stage}, Name: {match_name}")
            if len(all_match_ids) > 10:
                print(f"  ... and {len(all_match_ids) - 10} more")
            conn.close()
            return 0
        
        match_ids_list = list(all_match_ids)
        print(f"\nDeleting {len(match_ids_list)} showmatch(es)...")
        
        # Delete player stats for these matches
        placeholders = ','.join('?' * len(match_ids_list))
        cur.execute(f"DELETE FROM Player_Stats WHERE match_id IN ({placeholders})", match_ids_list)
        player_stats_deleted = cur.rowcount
        
        # Delete maps for these matches
        cur.execute(f"DELETE FROM Maps WHERE match_id IN ({placeholders})", match_ids_list)
        maps_deleted = cur.rowcount
        
        # Delete matches
        cur.execute(f"DELETE FROM Matches WHERE match_id IN ({placeholders})", match_ids_list)
        matches_deleted = cur.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"\nDeleted:")
        print(f"  {matches_deleted} match(es)")
        print(f"  {maps_deleted} map(s)")
        print(f"  {player_stats_deleted} player stat record(s)")
        return 0


if __name__ == "__main__":
    main()
