"""
Relabel mislabeled teams using player primary-team inference and tournament region hints.

Rules:
- For matches in 2024/2025 where team is Gen.G or Global Esports, infer side by majority of players' primary team.
- For matches with TYLOO/Talon: if tournament name contains 'china' then team should be TYLOO; otherwise, leave as is. If a side is TYLOO and tournament does NOT contain 'china', relabel to Talon Esports. If a side is Talon Esports and tournament DOES contain 'china', relabel to TYLOO.

Primary team per player = most frequent team in Player_Stats overall.
"""
import sqlite3
from collections import defaultdict, Counter

DB_PATH = "valorant_esports.db"


def build_player_primary_team(cur):
    cur.execute(
        """
        SELECT player, team, COUNT(*) as c
        FROM Player_Stats
        WHERE player IS NOT NULL AND team IS NOT NULL
        GROUP BY player, team
        """
    )
    rows = cur.fetchall()
    primary = {}
    for player, team, c in rows:
        if player is None or team is None:
            continue
        prev = primary.get(player)
        if prev is None or c > prev[1]:
            primary[player] = (team, c)
    return {p: t for p, (t, _) in primary.items()}


def infer_team_from_players(cur, match_id, current_team_name, primary_map):
    players = cur.execute(
        "SELECT DISTINCT player FROM Player_Stats WHERE match_id=?",
        (match_id,),
    ).fetchall()
    votes = Counter()
    for (player,) in players:
        if player in primary_map:
            votes[primary_map[player]] += 1
    if not votes:
        return current_team_name  # no signal
    inferred, count = votes.most_common(1)[0]
    return inferred


def relabel_gen_g_global(cur, primary_map):
    # Only 2024/2025
    rows = cur.execute(
        """
        SELECT match_id, team_a, team_b
        FROM Matches
        WHERE match_date LIKE '2024%' OR match_date LIKE '2025%'
          AND (team_a IN ('Gen.G','Global Esports') OR team_b IN ('Gen.G','Global Esports'))
        """
    ).fetchall()

    for match_id, ta, tb in rows:
        changed = False
        new_ta, new_tb = ta, tb

        if ta in ("Gen.G", "Global Esports"):
            inferred = infer_team_from_players(cur, match_id, ta, primary_map)
            if inferred != ta and inferred in ("Gen.G", "Global Esports"):
                new_ta = inferred
                changed = True

        if tb in ("Gen.G", "Global Esports"):
            inferred = infer_team_from_players(cur, match_id, tb, primary_map)
            if inferred != tb and inferred in ("Gen.G", "Global Esports"):
                new_tb = inferred
                changed = True

        if changed:
            cur.execute("UPDATE Matches SET team_a=?, team_b=? WHERE match_id=?", (new_ta, new_tb, match_id))
            # Update player rows that used the old team names for this match
            cur.execute("UPDATE Player_Stats SET team=? WHERE match_id=? AND team IN ('Gen.G','Global Esports')", (new_ta, match_id))
            cur.execute("UPDATE Player_Stats SET team=? WHERE match_id=? AND team IN ('Gen.G','Global Esports')", (new_tb, match_id))


def relabel_talon_tyloo(cur):
    rows = cur.execute(
        """
        SELECT match_id, team_a, team_b, tournament
        FROM Matches
        WHERE team_a IN ('Talon Esports','TYLOO') OR team_b IN ('Talon Esports','TYLOO')
        """
    ).fetchall()

    for match_id, ta, tb, tournament in rows:
        t = (tournament or "").lower()
        is_china = "china" in t
        new_ta, new_tb = ta, tb
        changed = False

        if ta == "Talon Esports" and is_china:
            new_ta = "TYLOO"; changed = True
        if ta == "TYLOO" and not is_china:
            new_ta = "Talon Esports"; changed = True

        if tb == "Talon Esports" and is_china:
            new_tb = "TYLOO"; changed = True
        if tb == "TYLOO" and not is_china:
            new_tb = "Talon Esports"; changed = True

        if changed:
            cur.execute("UPDATE Matches SET team_a=?, team_b=? WHERE match_id=?", (new_ta, new_tb, match_id))
            cur.execute("UPDATE Player_Stats SET team=? WHERE match_id=? AND team IN ('Talon Esports','TYLOO')", (new_ta, match_id))
            cur.execute("UPDATE Player_Stats SET team=? WHERE match_id=? AND team IN ('Talon Esports','TYLOO')", (new_tb, match_id))


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    primary_map = build_player_primary_team(cur)
    relabel_gen_g_global(cur, primary_map)
    relabel_talon_tyloo(cur)

    conn.commit()
    conn.close()
    print("Relabel complete.")


if __name__ == "__main__":
    main()