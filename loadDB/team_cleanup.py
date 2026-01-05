import os
import re
import sqlite3

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'valorant_esports.db'))

ALIASES = [
    (re.compile(r"^guangzhou\s+huadu\s+bilibili\s+gaming(?:\(bilibili\s+gaming\))?$", re.I), "Bilibili Gaming"),
    (re.compile(r"^bilibili\s+gaming$", re.I), "Bilibili Gaming"),
]

def normalize(name: str) -> str:
    if not name:
        return name
    n = name.strip()
    for pat, canon in ALIASES:
        if pat.search(n):
            return canon
    return n

def run():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Update Matches team_a/team_b
    cur.execute("SELECT DISTINCT team_a FROM Matches")
    teams_a = [r[0] for r in cur.fetchall() if r[0] is not None]
    cur.execute("SELECT DISTINCT team_b FROM Matches")
    teams_b = [r[0] for r in cur.fetchall() if r[0] is not None]
    teams = set(teams_a + teams_b)

    updates = []
    for t in teams:
        canon = normalize(t)
        if canon != t:
            updates.append((canon, t))

    for canon, old in updates:
        cur.execute("UPDATE Matches SET team_a = ? WHERE team_a = ?", (canon, old))
        cur.execute("UPDATE Matches SET team_b = ? WHERE team_b = ?", (canon, old))

    # Update Player_Stats team field
    cur.execute("SELECT DISTINCT team FROM Player_Stats")
    pteams = [r[0] for r in cur.fetchall() if r[0] is not None]
    for t in pteams:
        canon = normalize(t)
        if canon != t:
            cur.execute("UPDATE Player_Stats SET team = ? WHERE team = ?", (canon, t))

    conn.commit()
    conn.close()
    print(f"Team cleanup complete. Updated {len(updates)} team name variants to canonical forms.")

if __name__ == "__main__":
    run()
