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
        compute_elo(save=args.save, top=args.top)
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
        import sqlite3
        
        conn = get_conn()
        cur = conn.cursor()
        
        # Count showmatches
        cur.execute("SELECT COUNT(*) FROM Matches WHERE match_type = 'SHOWMATCH'")
        count = cur.fetchone()[0]
        
        if count == 0:
            print("No showmatches found in database.")
            conn.close()
            return 0
        
        if args.dry_run:
            print(f"DRY RUN: Would delete {count} showmatch(es)")
            cur.execute("SELECT match_id, team_a, team_b, match_name FROM Matches WHERE match_type = 'SHOWMATCH' LIMIT 10")
            matches = cur.fetchall()
            print("\nSample matches that would be deleted:")
            for match_id, team_a, team_b, match_name in matches:
                print(f"  Match {match_id}: {team_a} vs {team_b} ({match_name})")
            if count > 10:
                print(f"  ... and {count - 10} more")
            conn.close()
            return 0
        
        # Get all showmatch IDs
        cur.execute("SELECT match_id FROM Matches WHERE match_type = 'SHOWMATCH'")
        match_ids = [row[0] for row in cur.fetchall()]
        
        print(f"Deleting {len(match_ids)} showmatch(es)...")
        
        # Delete player stats for these matches
        cur.execute("DELETE FROM Player_Stats WHERE match_id IN ({})".format(','.join('?' * len(match_ids))), match_ids)
        player_stats_deleted = cur.rowcount
        
        # Delete maps for these matches
        cur.execute("DELETE FROM Maps WHERE match_id IN ({})".format(','.join('?' * len(match_ids))), match_ids)
        maps_deleted = cur.rowcount
        
        # Delete matches
        cur.execute("DELETE FROM Matches WHERE match_type = 'SHOWMATCH'")
        matches_deleted = cur.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"Deleted:")
        print(f"  {matches_deleted} match(es)")
        print(f"  {maps_deleted} map(s)")
        print(f"  {player_stats_deleted} player stat record(s)")
        return 0


if __name__ == "__main__":
    main()
