import sqlite3
import os
import argparse

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'valorant_esports.db'))

def fetch_one_match(cursor, match_name: str | None, match_id: int | None):
    if match_id is not None:
        cursor.execute("SELECT match_id, tournament, stage, match_type, match_name, team_a, team_b, team_a_score, team_b_score, match_result FROM Matches WHERE match_id = ? LIMIT 1", (match_id,))
    elif match_name:
        cursor.execute("SELECT match_id, tournament, stage, match_type, match_name, team_a, team_b, team_a_score, team_b_score, match_result FROM Matches WHERE match_name = ? LIMIT 1", (match_name,))
    else:
        cursor.execute("SELECT match_id, tournament, stage, match_type, match_name, team_a, team_b, team_a_score, team_b_score, match_result FROM Matches ORDER BY RANDOM() LIMIT 1")
    return cursor.fetchone()

def print_match_summary(conn, match_name: str | None, match_id: int | None):
    cur = conn.cursor()
    row = fetch_one_match(cur, match_name, match_id)
    if not row:
        print("No matches found in Matches.")
        return
    match_id, tournament, stage, match_type, match_name, team_a, team_b, a_score, b_score, match_result = row
    print(f"Match: {match_name}")
    print(f"Match ID: {match_id}")
    print(f"Tournament: {tournament} | Stage: {stage} | Type: {match_type}")
    print(f"Teams: {team_a} vs {team_b}")
    print(f"Series Score: {a_score}-{b_score}")
    print(f"Result: {match_result}")

    cur.execute("SELECT id, game_id, map, team_a_score, team_b_score FROM Maps WHERE match_id = ? ORDER BY id", (match_id,))
    maps = cur.fetchall()
    if maps:
        print(f"Maps Played ({len(maps)}): {', '.join(m[2] for m in maps)}")
        print("Per-Map Scores:")
        for mid, gid, mname, tas, tbs in maps:
            print(f"  {mname} (game {gid}): {team_a} {tas} - {tbs} {team_b}")
    else:
        print("Maps Played (0): None")

    cur.execute("SELECT map_id, game_id, player, team, agent, rating, acs, kills, deaths, assists FROM Player_Stats WHERE match_id = ? ORDER BY map_id, rating DESC LIMIT 10", (match_id,))
    overview_rows = cur.fetchall()
    if overview_rows:
        print("Sample Player Stats (up to 10):")
        for map_id, game_id, player, team, agent, rating, acs, k, d, a in overview_rows:
            # Find map name for display
            cur.execute("SELECT map FROM Maps WHERE id = ?", (map_id,))
            map_row = cur.fetchone()
            mname = map_row[0] if map_row else 'Unknown'
            print(f"  [{mname}] {player} ({team}) {agent} | Rating {rating} ACS {acs} K/D/A {k}/{d}/{a}")
    else:
        print("Player Stats: None")

def main():
    parser = argparse.ArgumentParser(description="Inspect match data from the SQLite DB")
    parser.add_argument("--match", dest="match_name", help="Exact match name to inspect (default: random selection)")
    parser.add_argument("--id", dest="match_id", type=int, help="Exact numeric match_id to inspect")
    parser.add_argument("--count", dest="count", type=int, default=3, help="Number of random matches to display (default: 3)")
    args = parser.parse_args()
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        if args.match_name or args.match_id is not None:
            print_match_summary(conn, args.match_name, args.match_id)
        else:
            cur = conn.cursor()
            cur.execute("SELECT match_name FROM Matches ORDER BY RANDOM() LIMIT ?", (args.count,))
            rows = cur.fetchall()
            if not rows:
                print("No matches found in Matches.")
                return
            for (mn,) in rows:
                print_match_summary(conn, mn, None)
                print("-")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
