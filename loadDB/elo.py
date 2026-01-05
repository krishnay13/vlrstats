import argparse
import math
import os
import sqlite3
from collections import defaultdict

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'valorant_esports.db'))

START_ELO = 1500.0
K_BASE = 25.0


TEAM_ALIASES = {
    # Normalize variations to canonical names
    # Bilibili Gaming and variants
    'guangzhou huadu bilibili gaming(bilibili gaming)': 'Bilibili Gaming',
    'guangzhou huadu bilibili gaming': 'Bilibili Gaming',
    'bilibili gaming': 'Bilibili Gaming',
}

def normalize_team(name: str | None) -> str:
    if not name:
        return ''
    n = name.strip()
    key = n.lower()
    return TEAM_ALIASES.get(key, n)

def get_importance(tournament: str, stage: str, match_type: str) -> float:
    t = (tournament or '').lower()
    s = (stage or '').lower()
    m = (match_type or '').lower()

    # Tournament category
    if 'champions' in t:
        t_w = 1.7
    elif 'masters' in t:
        t_w = 1.6
    elif 'kickoff' in t or 'stage 1' in t or 'stage 2' in t:
        t_w = 1.0
    else:
        t_w = 1.0

    # Match type weighting within tournament
    if any(x in m for x in ['grand final']):
        m_w = 1.5
    elif any(x in m for x in ['lower final', 'upper final']):
        m_w = 1.4
    elif 'semifinal' in m or 'semi-final' in m:
        m_w = 1.35
    elif 'quarterfinal' in m or 'quarter-final' in m:
        m_w = 1.3
    elif 'playoffs' in m:
        m_w = 1.2
    elif any(x in m for x in ['elimination', 'decider']):
        m_w = 1.15
    elif any(x in m for x in ['week', 'group stage', 'swiss']):
        m_w = 1.0
    else:
        # Fallback: check stage token for group/playoff indicators
        if 'playoff' in s:
            m_w = 1.2
        else:
            m_w = 1.0

    return t_w * m_w


def expected_score(r_a: float, r_b: float) -> float:
    return 1.0 / (1.0 + math.pow(10.0, (r_b - r_a) / 400.0))


def mov_multiplier(margin: int, rdiff: float) -> float:
    # Classic Elo MOV adjustment used in basketball elo
    # ln(1+margin) * 2.2 / (rdiff*0.001 + 2.2)
    return math.log(1 + max(1, margin)) * 2.2 / (abs(rdiff) * 0.001 + 2.2)


def compute_elo(save: bool = False, top: int = 20):
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"DB not found at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Load matches; without timestamps we approximate order by match_id
    cur.execute("""
        SELECT match_id, tournament, stage, match_type, match_name, team_a, team_b, team_a_score, team_b_score
        FROM Matches
        WHERE team_a IS NOT NULL AND team_b IS NOT NULL
        ORDER BY match_id ASC
    """)
    matches = cur.fetchall()

    ratings = defaultdict(lambda: START_ELO)
    games_played = defaultdict(int)
    history_rows = []

    for match_id, tournament, stage, match_type, match_name, ta, tb, ta_score, tb_score in matches:
        try:
            a = normalize_team(ta)
            b = normalize_team(tb)
            if not a or not b:
                continue
            if ta_score is None or tb_score is None:
                continue
            if ta_score == tb_score == 0:
                # likely unknown result
                continue

            ra = ratings[a]
            rb = ratings[b]
            exp_a = expected_score(ra, rb)
            exp_b = 1.0 - exp_a

            # Actual result (series winner)
            if ta_score > tb_score:
                sa, sb = 1.0, 0.0
                margin = ta_score - tb_score
            elif tb_score > ta_score:
                sa, sb = 0.0, 1.0
                margin = tb_score - ta_score
            else:
                sa, sb = 0.5, 0.5
                margin = 0

            rdiff = ra - rb
            k = K_BASE
            imp = get_importance(tournament or '', stage or '', match_type or '')
            mult = mov_multiplier(margin, rdiff)
            k_eff = k * imp * mult

            # Update ratings
            new_ra = ra + k_eff * (sa - exp_a)
            new_rb = rb + k_eff * (sb - exp_b)

            if save:
                history_rows.append((match_id, a, b, ra, new_ra, exp_a, sa, margin, k_eff, imp))
                history_rows.append((match_id, b, a, rb, new_rb, exp_b, sb, margin, k_eff, imp))

            ratings[a] = new_ra
            ratings[b] = new_rb
            games_played[a] += 1
            games_played[b] += 1
        except Exception as e:
            print(f"[WARN] Skipping match {match_id} due to error: {e}")
            continue

    if save:
        cur.executemany(
            """
            INSERT INTO Elo_History (match_id, team, opponent, pre_rating, post_rating, expected, actual, margin, k_used, importance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            history_rows,
        )
        # Replace current snapshot
        cur.execute("DELETE FROM Elo_Current")
        cur.executemany(
            """
            INSERT INTO Elo_Current (team, rating, matches, last_match_id)
            VALUES (?, ?, ?, ?)
            """,
            [(t, ratings[t], games_played[t], None) for t in ratings.keys()],
        )
        conn.commit()

    # Print top N
    top_list = sorted(ratings.items(), key=lambda x: x[1], reverse=True)[: top]
    print("Top Teams by Elo:")
    for i, (team, rating) in enumerate(top_list, 1):
        print(f"{i:2d}. {team:30s} {rating:7.2f} ({games_played[team]} matches)")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute Elo ratings from Matches table")
    parser.add_argument("--save", action="store_true", help="Save Elo history and current ratings to DB")
    parser.add_argument("--top", type=int, default=20, help="Number of top teams to display")
    parser.add_argument("--team", type=str, help="Show Elo history breakdown for a specific team")
    args = parser.parse_args()
    compute_elo(save=args.save, top=args.top)

    if args.team:
        team = normalize_team(args.team)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT h.match_id, m.tournament, m.stage, m.match_type, m.match_name,
                   h.team, h.opponent, h.pre_rating, h.post_rating, h.expected, h.actual, h.margin, h.k_used, h.importance
            FROM Elo_History h
            LEFT JOIN Matches m ON m.match_id = h.match_id
            WHERE LOWER(h.team) = LOWER(?)
            ORDER BY h.match_id ASC
            """,
            (team,),
        )
        rows = cur.fetchall()
        print(f"\nElo history for {team}:")
        for (match_id, tournament, stage, match_type, match_name, t, opp, pre, post, exp, act, margin, k_used, imp) in rows:
            delta = post - pre
            context = f"{tournament} | {stage} | {match_type}" if tournament or stage or match_type else ""
            print(f"#{match_id} {context} vs {opp}: pre {pre:.2f} -> post {post:.2f} (Δ {delta:+.2f}); exp {exp:.2f}, act {act:.2f}, margin {margin}, k_eff {k_used:.2f}, imp {imp:.2f}")
        conn.close()
