import os
import sqlite3

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'valorant_esports.db'))

def run():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Delete unplayed maps where scores are NULL
    cur.execute("DELETE FROM Maps WHERE team_a_score IS NULL OR team_b_score IS NULL")
    deleted = cur.rowcount

    conn.commit()
    conn.close()
    print(f"Deleted {deleted} unplayed map rows.")

if __name__ == "__main__":
    run()
