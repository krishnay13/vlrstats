import argparse
from . import vlr_ingest
from .elo import compute_elo
from .display import top_players, top_teams, team_history, player_history


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


if __name__ == "__main__":
    main()
