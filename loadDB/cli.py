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
    p_topteams.add_argument("-n", type=int, default=20)
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
    p_upload_file.add_argument("--match-type", choices=["VCL", "OFFSEASON", "VCT", "SHOWMATCH"], help="Match type (VCL, OFFSEASON, VCT, or SHOWMATCH)")

    p_scrape_all_vct = sub.add_parser("scrape-all-vct", help="Clear DB and scrape all VCT 2024 & 2025 matches")
    
    p_test_matches = sub.add_parser("test-matches", help="Test random matches for data quality")
    p_test_matches.add_argument("-n", "--num", type=int, default=10, help="Number of random matches to test")

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
            for i, (team, rating, matches) in enumerate(top_teams(args.n), 1):
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
                user_input = input("Enter match type (VCL, OFFSEASON, VCT, or SHOWMATCH): ").strip().upper()
                if user_input in ["VCL", "OFFSEASON", "VCT", "SHOWMATCH"]:
                    match_type = user_input
                    break
                else:
                    print("Invalid input. Please enter VCL, OFFSEASON, VCT, or SHOWMATCH.")
        
        print(f"Uploading {len(match_ids)} match(es) with match type: {match_type}")
        try:
            vlr_ingest.ingest(match_ids, match_type=match_type)
            print(f"Successfully uploaded {len(match_ids)} match(es)")
        except Exception as e:
            print(f"Error uploading matches: {e}")
            return 1

    if args.cmd == "scrape-all-vct":
        from .scrape_all_vct import main as scrape_main
        asyncio.run(scrape_main())
        return

    if args.cmd == "test-matches":
        from .test_matches import test_random_matches
        test_random_matches(args.num)
        return


if __name__ == "__main__":
    main()
