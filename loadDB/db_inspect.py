import sqlite3
import os
import argparse

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'valorant_esports.db'))

def fetch_one_match(cursor, match_name: str | None):
    if match_name:
        cursor.execute("SELECT match_id, tournament, stage, match_type, match_name, team_a, team_b, team_a_score, team_b_score, match_result FROM Scores WHERE match_name = ? LIMIT 1", (match_name,))
    else:
        cursor.execute("SELECT match_id, tournament, stage, match_type, match_name, team_a, team_b, team_a_score, team_b_score, match_result FROM Scores LIMIT 1")
    return cursor.fetchone()

def print_match_summary(conn, match_name: str | None):
    cur = conn.cursor()
    row = fetch_one_match(cur, match_name)
    if not row:
        print("No matches found in Scores.")
        return
    match_id, tournament, stage, match_type, match_name, team_a, team_b, a_score, b_score, match_result = row
    print(f"Match: {match_name}")
    print(f"Match ID: {match_id}")
    print(f"Tournament: {tournament} | Stage: {stage} | Type: {match_type}")
    print(f"Teams: {team_a} vs {team_b}")
    print(f"Series Score: {a_score}-{b_score}")
    print(f"Result: {match_result}")

    cur.execute("SELECT map FROM MapsPlayed WHERE match_id = ?", (match_id,))
    maps = [m[0] for m in cur.fetchall()]
    print(f"Maps Played ({len(maps)}): {', '.join(maps) if maps else 'None'}")

    cur.execute("SELECT map, team_a, team_a_score, team_b, team_b_score FROM MapScores WHERE match_id = ?", (match_id,))
    map_scores = cur.fetchall()
    if map_scores:
        print("Per-Map Scores:")
        for mname, ta, tas, tb, tbs in map_scores:
            print(f"  {mname}: {ta} {tas} - {tbs} {tb}")
    else:
        print("Per-Map Scores: None")

    cur.execute("SELECT map, player, team, agents, rating, average_combat_score, kills, deaths, assists FROM Overview WHERE match_id = ? LIMIT 10", (match_id,))
    overview_rows = cur.fetchall()
    if overview_rows:
        print("Sample Player Overview (up to 10):")
        for mname, player, team, agent, rating, acs, k, d, a in overview_rows:
            print(f"  [{mname}] {player} ({team}) {agent} | Rating {rating} ACS {acs} K/D/A {k}/{d}/{a}")
    else:
        print("Overview: None")

def main():
    parser = argparse.ArgumentParser(description="Inspect match data from the SQLite DB")
    parser.add_argument("--match", dest="match_name", help="Exact match name to inspect (default: random selection)")
    parser.add_argument("--count", dest="count", type=int, default=3, help="Number of random matches to display (default: 3)")
    args = parser.parse_args()
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        if args.match_name:
            print_match_summary(conn, args.match_name)
        else:
            cur = conn.cursor()
            cur.execute("SELECT match_name FROM Scores ORDER BY RANDOM() LIMIT ?", (args.count,))
            rows = cur.fetchall()
            if not rows:
                print("No matches found in Scores.")
                return
            for (mn,) in rows:
                print_match_summary(conn, mn)
                print("-")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
