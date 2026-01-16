"""Fix Gen.G vs Global Esports mislabels using match_name text.

Logic:
- Find matches where team_a or team_b is Gen.G or Global Esports.
- Inspect match_name (case-insensitive) for explicit team text:
    * if contains 'global esports' -> label should be Global Esports
    * if contains 'gen.g' -> label should be Gen.G
  If both appear, skip (ambiguous). If neither appears, leave unchanged.
- When relabeling a side, also relabel Player_Stats rows for that match where team matches the old label.
"""
import sqlite3

DB_PATH = "valorant_esports.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    rows = cur.execute(
        """
        SELECT match_id, team_a, team_b, match_name
        FROM Matches
        WHERE team_a IN ('Gen.G','Global Esports') OR team_b IN ('Gen.G','Global Esports')
        """
    ).fetchall()

    updates = []
    for match_id, ta, tb, name in rows:
        text = (name or "").lower()
        has_global = "global esports" in text
        has_geng = "gen.g" in text or "gen g" in text
        # skip ambiguous or no signal
        if has_global and has_geng:
            continue
        new_ta, new_tb = ta, tb
        changed = False
        # check team_a
        if ta in ("Gen.G", "Global Esports"):
            if has_global and ta != "Global Esports":
                new_ta = "Global Esports"; changed = True
            if has_geng and ta != "Gen.G":
                new_ta = "Gen.G"; changed = True
        # check team_b
        if tb in ("Gen.G", "Global Esports"):
            if has_global and tb != "Global Esports":
                new_tb = "Global Esports"; changed = True
            if has_geng and tb != "Gen.G":
                new_tb = "Gen.G"; changed = True
        if changed:
            updates.append((match_id, ta, tb, new_ta, new_tb))
            cur.execute("UPDATE Matches SET team_a=?, team_b=? WHERE match_id=?", (new_ta, new_tb, match_id))
            cur.execute("UPDATE Player_Stats SET team=? WHERE match_id=? AND team=?", (new_ta, match_id, ta))
            cur.execute("UPDATE Player_Stats SET team=? WHERE match_id=? AND team=?", (new_tb, match_id, tb))

    conn.commit()
    conn.close()

    print(f"Processed {len(rows)} candidate matches; relabeled {len(updates)}")
    if updates:
        print("Sample updates (match_id, old_a, old_b, new_a, new_b):")
        for item in updates[:10]:
            print(item)


if __name__ == "__main__":
    main()