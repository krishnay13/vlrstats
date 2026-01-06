import argparse
import math
import os
import sqlite3
from collections import defaultdict
from statistics import mean
import unicodedata
from .config import (
    DB_PATH,
    START_ELO,
    K_BASE,
    PLAYER_START_ELO,
    K_PLAYER_BASE,
    PLAYER_INFLUENCE_BETA,
    PLAYER_WEIGHT_EQUAL_BLEND,
    PLAYER_MAX_SHARE_FRACTION,
    RATING_RELATIVE_CLIP_LOW,
    RATING_RELATIVE_CLIP_HIGH,
    PLAYER_RATING_WEIGHT,
    PLAYER_ACS_WEIGHT,
    PLAYER_PERF_LOGIT_BETA,
    WIN_LOSS_WEIGHT,
    PLAYER_DELTA_CAP,
    PLAYER_SEED_SCALE,
    TEAM_ALIASES,
)

 

def normalize_team(name: str | None) -> str:
    if not name:
        return ''
    n = name.strip()
    key = n.lower()
    return TEAM_ALIASES.get(key, n)

def canon(name: str | None) -> str:
    """Canonicalize a team name for robust equality: lowercase and remove non-alphanumerics."""
    if not name:
        return ''
    s = normalize_team(name)
    s = s.lower()
    # Strip diacritics (e.g., ü -> u)
    s_norm = unicodedata.normalize('NFKD', s)
    s_no_accents = ''.join(ch for ch in s_norm if not unicodedata.combining(ch))
    return ''.join(ch for ch in s_no_accents if ch.isalnum())

def get_importance(tournament: str, stage: str, match_type: str) -> float:
    t = (tournament or '').lower()
    s = (stage or '').lower()
    m = (match_type or '').lower()

    # Tournament category (increase gap for internationals)
    if 'champions' in t:
        t_w = 2.0
    elif 'masters' in t:
        # Masters weighting by location/year: downweight Bangkok, keep Toronto closer to Champions
        if 'bangkok' in t:
            t_w = 1.7
        elif 'toronto' in t:
            t_w = 1.9
        else:
            t_w = 1.8
    elif 'kickoff' in t or 'stage 1' in t or 'stage 2' in t:
        t_w = 1.0
    else:
        t_w = 1.0

    # Match type weighting within tournament (reintroduced)
    if any(x in m for x in ['grand final']):
        m_w = 1.45
    elif any(x in m for x in ['lower final', 'upper final']):
        m_w = 1.35
    elif 'semifinal' in m or 'semi-final' in m:
        m_w = 1.30
    elif 'quarterfinal' in m or 'quarter-final' in m:
        m_w = 1.25
    elif 'playoffs' in m:
        m_w = 1.15
    elif any(x in m for x in ['elimination', 'decider']):
        m_w = 1.10
    elif any(x in m for x in ['week', 'group stage', 'swiss']):
        m_w = 1.0
    else:
        # Fallback: check stage token for group/playoff indicators
        if 'playoff' in s:
            m_w = 1.15
        else:
            m_w = 1.0
    return t_w * m_w


def expected_score(r_a: float, r_b: float) -> float:
    return 1.0 / (1.0 + math.pow(10.0, (r_b - r_a) / 400.0))


def mov_multiplier(margin: int, rdiff: float) -> float:
    # Classic Elo MOV adjustment used in basketball elo
    # ln(1+margin) * 2.2 / (rdiff*0.001 + 2.2)
    return math.log(1 + max(1, margin)) * 2.2 / (abs(rdiff) * 0.001 + 2.2)


def get_round_margin(cur: sqlite3.Cursor, match_id: int) -> float | None:
    """Compute a normalized round-based margin for a match.

    - Aggregates total rounds won for team A and B across played maps
    - Normalizes by number of maps to get an average per-map round margin
    - Scales down (divide by 2) and clamps to [1, 8] to prevent inflation
    Returns None if map scores are unavailable.
    """
    try:
        cur.execute(
            """
            SELECT COALESCE(SUM(team_a_score), 0), COALESCE(SUM(team_b_score), 0), COUNT(*)
            FROM Maps
            WHERE match_id = ?
            """,
            (match_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        total_a, total_b, maps_played = row
        # If both totals are zero or no maps, treat as unavailable
        if ((total_a or 0) == 0 and (total_b or 0) == 0) or (maps_played or 0) == 0:
            return None
        raw_round_margin = abs(float(total_a) - float(total_b))
        avg_round_margin = raw_round_margin / float(maps_played)
        # Scale down and clamp to a sensible range
        scaled = avg_round_margin / 2.0
        return float(max(1.0, min(8.0, scaled)))
    except Exception:
        return None


def get_team_roster(cur: sqlite3.Cursor, match_id: int, team: str) -> list[str]:
    """Return distinct players for a given match whose normalized team matches.

    This avoids strict string equality by normalizing Player_Stats.team values.
    """
    cur.execute(
        """
        SELECT DISTINCT player, team
        FROM Player_Stats
        WHERE match_id = ?
        """,
        (match_id,),
    )
    rows = cur.fetchall()
    target = canon(team)
    roster: list[str] = []
    for player, t in rows:
        if not player:
            continue
        if canon(t) == target:
            roster.append(player)
    return roster


def get_match_stat_averages(cur: sqlite3.Cursor, match_id: int) -> tuple[float, float]:
    """Return (avg_rating, avg_acs) across all players in the match."""
    cur.execute(
        """
        SELECT AVG(rating), AVG(acs)
        FROM Player_Stats
        WHERE match_id = ?
        """,
        (match_id,),
    )
    row = cur.fetchone()
    avg_rating = float(row[0]) if row and row[0] is not None else 1.0
    avg_acs = float(row[1]) if row and row[1] is not None else 200.0
    return avg_rating, avg_acs


def get_player_stat_averages(cur: sqlite3.Cursor, match_id: int, player: str) -> tuple[float, float]:
    """Return (avg_rating, avg_acs) for a single player in the match across maps."""
    cur.execute(
        """
        SELECT AVG(rating), AVG(acs)
        FROM Player_Stats
        WHERE match_id = ? AND player = ?
        """,
        (match_id, player),
    )
    row = cur.fetchone()
    p_rating = float(row[0]) if row and row[0] is not None else 1.0
    p_acs = float(row[1]) if row and row[1] is not None else 200.0
    return p_rating, p_acs


def _cap_shares(shares: list[float], cap: float) -> list[float]:
    """Cap each share to `cap` and redistribute excess proportionally.

    Assumes `shares` sums to ~1. Returns a new list summing to 1
    with each element <= cap. Handles edge cases robustly.
    """
    n = len(shares)
    if n == 0:
        return []
    # Normalize to sum 1
    total = sum(shares) or 1.0
    shares = [s / total for s in shares]
    # Iteratively cap and redistribute
    while True:
        over_idx = [i for i, s in enumerate(shares) if s > cap]
        if not over_idx:
            break
        excess = sum(shares[i] - cap for i in over_idx)
        for i in over_idx:
            shares[i] = cap
        under_idx = [i for i in range(n) if i not in over_idx]
        remaining = sum(shares[i] for i in under_idx)
        # If no remaining to redistribute, spread equally among under_idx
        if not under_idx:
            # All capped; normalize to sum 1 by slight scaling
            scale = 1.0 / sum(shares)
            shares = [s * scale for s in shares]
            break
        if remaining <= 0:
            add_each = excess / len(under_idx)
            for i in under_idx:
                shares[i] += add_each
        else:
            scale = (1.0 - sum(shares[i] for i in over_idx)) / remaining
            for i in under_idx:
                shares[i] *= scale
        # Loop again in case scaling pushed someone over cap
    # Final normalize
    total = sum(shares) or 1.0
    return [max(0.0, s / total) for s in shares]


def compute_rating_shares(cur: sqlite3.Cursor, match_id: int, team: str, roster: list[str]) -> list[tuple[str, float]]:
    """Compute per-player shares using ONLY rating.

    - For players with 0.0 or missing rating, approximate using team non-zero rating mean;
      if none exists, fall back to match-wide average rating or 1.0.
    - Clip relative ratings to moderate extremes.
    - Blend rating-proportional weights with equal share to limit dominance.
    - Cap final shares so no single player exceeds PLAYER_MAX_SHARE_FRACTION.
    Returns list of (player, share). Sum of shares is 1.0.
    """
    if not roster:
        return []
    # Fetch raw ratings per player
    raw: list[float] = []
    for p in roster:
        p_rating, _ = get_player_stat_averages(cur, match_id, p)
        raw.append(float(p_rating or 0.0))
    # Team non-zero mean
    non_zero = [r for r in raw if r > 0.0]
    # Match-wide average rating as fallback
    cur.execute(
        """
        SELECT AVG(rating)
        FROM Player_Stats
        WHERE match_id = ? AND team = ?
        """,
        (match_id, team),
    )
    row = cur.fetchone()
    team_avg = float(row[0]) if row and row[0] is not None else None
    cur.execute(
        """
        SELECT AVG(rating)
        FROM Player_Stats
        WHERE match_id = ?
        """,
        (match_id,),
    )
    row2 = cur.fetchone()
    match_avg = float(row2[0]) if row2 and row2[0] is not None else 1.0
    approx_base = (mean(non_zero) if non_zero else (team_avg if team_avg not in (None, 0.0) else match_avg)) or 1.0
    eff = [r if r > 0.0 else approx_base for r in raw]
    team_mean = mean(eff) if eff else 1.0
    # Relative ratings clipped to avoid extremes
    rel = [min(RATING_RELATIVE_CLIP_HIGH, max(RATING_RELATIVE_CLIP_LOW, (r / team_mean) if team_mean > 0 else 1.0)) for r in eff]
    total_rel = sum(rel) or float(len(rel))
    prop = [r / total_rel for r in rel]
    n = len(roster)
    equal = 1.0 / n
    shares = [PLAYER_WEIGHT_EQUAL_BLEND * prop[i] + (1.0 - PLAYER_WEIGHT_EQUAL_BLEND) * equal for i in range(n)]
    shares = _cap_shares(shares, PLAYER_MAX_SHARE_FRACTION)
    return list(zip(roster, shares))


def get_team_avg_rating(cur: sqlite3.Cursor, match_id: int, team: str) -> float | None:
    """Return average rating for a normalized team in a match (None if unavailable)."""
    cur.execute(
        """
        SELECT rating, team
        FROM Player_Stats
        WHERE match_id = ? AND rating IS NOT NULL
        """,
        (match_id,),
    )
    rows = cur.fetchall()
    target = canon(team)
    vals = [float(r) for (r, t) in rows if canon(t) == target and r is not None]
    if not vals:
        return None
    return float(sum(vals) / len(vals))


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
    # Player Elo tracking
    player_ratings = defaultdict(lambda: PLAYER_START_ELO)
    player_games = defaultdict(int)
    player_history_rows = []
    player_teams: dict[str, str | None] = {}

    for match_id, tournament, stage, match_type, match_name, ta, tb, ta_score, tb_score in matches:
        try:
            a = normalize_team(ta)
            b = normalize_team(tb)
            if not a or not b:
                continue

            ra = ratings[a]
            rb = ratings[b]

            # Rosters for opponent-aware computations
            roster_a = get_team_roster(cur, match_id, a)
            roster_b = get_team_roster(cur, match_id, b)
            avg_pa = mean([player_ratings[p] for p in roster_a]) if roster_a else PLAYER_START_ELO
            avg_pb = mean([player_ratings[p] for p in roster_b]) if roster_b else PLAYER_START_ELO
            ra_eff = ra + PLAYER_INFLUENCE_BETA * (avg_pa - PLAYER_START_ELO)
            rb_eff = rb + PLAYER_INFLUENCE_BETA * (avg_pb - PLAYER_START_ELO)

            exp_a = expected_score(ra_eff, rb_eff)
            exp_b = 1.0 - exp_a

            # Actual result (series winner); for unknown scores, use neutral 0.5 and skip team updates
            team_update = True
            if ta_score is None or tb_score is None or (ta_score == tb_score == 0):
                sa, sb = 0.5, 0.5
                margin = 0
                team_update = False
            else:
                if ta_score > tb_score:
                    sa, sb = 1.0, 0.0
                    margin = ta_score - tb_score
                elif tb_score > ta_score:
                    sa, sb = 0.0, 1.0
                    margin = tb_score - ta_score
                else:
                    sa, sb = 0.5, 0.5
                    margin = 0

            rdiff = ra_eff - rb_eff
            k = K_BASE
            imp = get_importance(tournament or '', stage or '', match_type or '')
            # Prefer round-based margin if available
            round_margin = get_round_margin(cur, match_id)
            use_margin = round_margin if round_margin is not None else float(margin)
            mult = mov_multiplier(use_margin, rdiff)
            k_eff = k * imp * mult

            # Update team ratings only when we have a known result
            new_ra = ra
            new_rb = rb
            if team_update:
                new_ra = ra + k_eff * (sa - exp_a)
                new_rb = rb + k_eff * (sb - exp_b)

            if save and team_update:
                # Store the margin actually used (round-based if present)
                history_rows.append((match_id, a, b, ra, new_ra, exp_a, sa, use_margin, k_eff, imp))
                history_rows.append((match_id, b, a, rb, new_rb, exp_b, sb, use_margin, k_eff, imp))

            ratings[a] = new_ra
            ratings[b] = new_rb
            games_played[a] += 1
            games_played[b] += 1

            # Player Elo update independent from team delta but opponent-aware;
            # expected vs average opponent player Elo; actual from rating-only or rating+ACS vs opponent team avg.
            # Player K scales with experience to stabilize ratings as matches increase
            # Use sqrt decay: k / sqrt(games+1)

            # Precompute match averages for fallbacks
            match_avg_rating, match_avg_acs = get_match_stat_averages(cur, match_id)

            # Team A players
            opp_avg_player_elo_a = mean([player_ratings[p] for p in roster_b]) if roster_b else PLAYER_START_ELO
            opp_team_avg_rating_a = get_team_avg_rating(cur, match_id, b)
            for p in roster_a:
                pre_p = player_ratings[p]
                exp_p = expected_score(pre_p, opp_avg_player_elo_a)
                p_rating, p_acs = get_player_stat_averages(cur, match_id, p)
                # Approximate missing/zero rating
                if p_rating <= 0.0:
                    approx = opp_team_avg_rating_a if (opp_team_avg_rating_a and opp_team_avg_rating_a > 0.0) else (match_avg_rating if match_avg_rating > 0.0 else 1.0)
                    p_rating = float(approx)
                opp_ref = opp_team_avg_rating_a if (opp_team_avg_rating_a and opp_team_avg_rating_a > 0.0) else (match_avg_rating if match_avg_rating > 0.0 else p_rating)
                r_ratio = p_rating / opp_ref if opp_ref > 0 else 1.0
                a_ratio = p_acs / match_avg_acs if (PLAYER_ACS_WEIGHT > 0 and match_avg_acs > 0) else 0.0
                perf_ratio = (PLAYER_RATING_WEIGHT * r_ratio) + (PLAYER_ACS_WEIGHT * a_ratio)
                base_actual = 1.0 / (1.0 + math.exp(-PLAYER_PERF_LOGIT_BETA * (perf_ratio - 1.0)))
                wl_adj = WIN_LOSS_WEIGHT * (sa - 0.5)
                actual_p = min(1.0, max(0.0, base_actual + wl_adj))
                # Per-player K with decay
                k_player_eff = K_PLAYER_BASE * imp / math.sqrt(max(1, player_games[p] + 1))
                delta = k_player_eff * (actual_p - exp_p)
                # Cap per-match change to avoid extreme swings
                delta = max(-PLAYER_DELTA_CAP, min(PLAYER_DELTA_CAP, delta))
                post_p = pre_p + delta
                player_history_rows.append((match_id, p, a, b, pre_p, post_p, exp_p, actual_p, None, k_player_eff, imp))
                player_ratings[p] = post_p
                player_games[p] += 1
                player_teams[p] = a

            # Team B players
            opp_avg_player_elo_b = mean([player_ratings[p] for p in roster_a]) if roster_a else PLAYER_START_ELO
            opp_team_avg_rating_b = get_team_avg_rating(cur, match_id, a)
            for p in roster_b:
                pre_p = player_ratings[p]
                exp_p = expected_score(pre_p, opp_avg_player_elo_b)
                p_rating, p_acs = get_player_stat_averages(cur, match_id, p)
                if p_rating <= 0.0:
                    approx = opp_team_avg_rating_b if (opp_team_avg_rating_b and opp_team_avg_rating_b > 0.0) else (match_avg_rating if match_avg_rating > 0.0 else 1.0)
                    p_rating = float(approx)
                opp_ref = opp_team_avg_rating_b if (opp_team_avg_rating_b and opp_team_avg_rating_b > 0.0) else (match_avg_rating if match_avg_rating > 0.0 else p_rating)
                r_ratio = p_rating / opp_ref if opp_ref > 0 else 1.0
                a_ratio = p_acs / match_avg_acs if (PLAYER_ACS_WEIGHT > 0 and match_avg_acs > 0) else 0.0
                perf_ratio = (PLAYER_RATING_WEIGHT * r_ratio) + (PLAYER_ACS_WEIGHT * a_ratio)
                base_actual = 1.0 / (1.0 + math.exp(-PLAYER_PERF_LOGIT_BETA * (perf_ratio - 1.0)))
                wl_adj = WIN_LOSS_WEIGHT * (sb - 0.5)
                actual_p = min(1.0, max(0.0, base_actual + wl_adj))
                k_player_eff = K_PLAYER_BASE * imp / math.sqrt(max(1, player_games[p] + 1))
                delta = k_player_eff * (actual_p - exp_p)
                delta = max(-PLAYER_DELTA_CAP, min(PLAYER_DELTA_CAP, delta))
                post_p = pre_p + delta
                player_history_rows.append((match_id, p, b, a, pre_p, post_p, exp_p, actual_p, None, k_player_eff, imp))
                player_ratings[p] = post_p
                player_games[p] += 1
                player_teams[p] = b
        except Exception as e:
            print(f"[WARN] Skipping match {match_id} due to error: {e}")
            continue

    if save:
        # Reset history before saving to avoid duplicates across runs
        cur.execute("DELETE FROM Elo_History")
        cur.executemany(
            """
            INSERT INTO Elo_History (match_id, team, opponent, pre_rating, post_rating, expected, actual, margin, k_used, importance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            history_rows,
        )
        # Save player Elo history
        cur.execute("DELETE FROM Player_Elo_History")
        cur.executemany(
            """
            INSERT INTO Player_Elo_History (match_id, player, team, opponent_team, pre_rating, post_rating, expected, actual, margin, k_used, importance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            player_history_rows,
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
        # Replace current snapshot with union of dynamic player ratings and seeds for all players in Player_Stats
        cur.execute("DELETE FROM Player_Elo_Current")

        # Global average rating for seeding
        cur.execute(
            """
            SELECT AVG(CASE WHEN rating > 0 THEN rating END)
            FROM Player_Stats
            """
        )
        row = cur.fetchone()
        global_avg_rating = float(row[0]) if row and row[0] is not None else 1.0

        # Most frequent team per player from Player_Stats
        cur.execute(
            """
            SELECT player, team, COUNT(*) as c
            FROM Player_Stats
            WHERE player IS NOT NULL AND team IS NOT NULL
            GROUP BY player, team
            """
        )
        team_counts = cur.fetchall()
        most_team: dict[str, tuple[str,int]] = {}
        for player, team, c in team_counts:
            if not player:
                continue
            prev = most_team.get(player)
            if prev is None or c > prev[1]:
                most_team[player] = (normalize_team(team), c)

        # Per-player averages and appearances for seeding
        cur.execute(
            """
            SELECT player,
                   AVG(CASE WHEN rating > 0 THEN rating END) AS avg_rating,
                   SUM(CASE WHEN rating IS NOT NULL THEN 1 ELSE 0 END) AS appearances
            FROM Player_Stats
            WHERE player IS NOT NULL
            GROUP BY player
            """
        )
        avg_rows = cur.fetchall()
        avg_map: dict[str, tuple[float|None,int]] = {p: (float(a) if a is not None else None, int(n) if n is not None else 0) for (p,a,n) in avg_rows}

        # Union set of players
        all_players = set(avg_map.keys()) | set(player_ratings.keys())
        to_insert = []
        for p in all_players:
            team = most_team.get(p, (None, 0))[0]
            if p in player_ratings:
                rating_val = player_ratings[p]
                matches_val = player_games.get(p, 0)
            else:
                avg_rating = avg_map.get(p, (None, 0))[0]
                appearances = avg_map.get(p, (None, 0))[1]
                if avg_rating is None:
                    rating_val = PLAYER_START_ELO
                else:
                    rating_val = START_ELO + PLAYER_SEED_SCALE * (float(avg_rating) - global_avg_rating)
                matches_val = appearances
            to_insert.append((p, team, float(rating_val), int(matches_val), None))

        cur.executemany(
            """
            INSERT INTO Player_Elo_Current (player, team, rating, matches, last_match_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            to_insert,
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
    parser.add_argument("--top-players", type=int, default=0, help="Number of top players to display from Player_Elo_Current")
    parser.add_argument("--team", type=str, help="Show Elo history breakdown for a specific team")
    parser.add_argument("--swings", action="store_true", help="Show largest positive/negative Elo swings")
    parser.add_argument("--limit", type=int, default=10, help="Number of swings to display per direction")
    args = parser.parse_args()
    compute_elo(save=args.save, top=args.top)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if args.top_players and args.top_players > 0:
        cur.execute(
            """
            SELECT player, team, rating, matches
            FROM Player_Elo_Current
            ORDER BY rating DESC
            LIMIT ?
            """,
            (args.top_players,),
        )
        rows = cur.fetchall()
        print("\nTop Players by Elo:")
        for i, (player, team, rating, matches) in enumerate(rows, 1):
            team_display = team if team else ""
            print(f"{i:2d}. {player:24s} {rating:7.2f} ({matches} matches) {team_display}")

    if args.team:
        team = normalize_team(args.team)
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

    if args.swings:
        if args.team:
            team = normalize_team(args.team)
            cur.execute(
                """
                SELECT h.match_id, m.tournament, m.stage, m.match_type, m.match_name,
                       h.team, h.opponent, (h.post_rating - h.pre_rating) AS delta, h.expected, h.actual, h.margin, h.k_used, h.importance
                FROM Elo_History h
                LEFT JOIN Matches m ON m.match_id = h.match_id
                WHERE LOWER(h.team) = LOWER(?)
                ORDER BY delta DESC
                LIMIT ?
                """,
                (team, args.limit),
            )
            pos_rows = cur.fetchall()
            cur.execute(
                """
                SELECT h.match_id, m.tournament, m.stage, m.match_type, m.match_name,
                       h.team, h.opponent, (h.post_rating - h.pre_rating) AS delta, h.expected, h.actual, h.margin, h.k_used, h.importance
                FROM Elo_History h
                LEFT JOIN Matches m ON m.match_id = h.match_id
                WHERE LOWER(h.team) = LOWER(?)
                ORDER BY delta ASC
                LIMIT ?
                """,
                (team, args.limit),
            )
            neg_rows = cur.fetchall()
            print(f"\nLargest swings for {team} (top {args.limit}):")
            print("  Positive:")
            for (match_id, tournament, stage, match_type, match_name, t, opp, delta, exp, act, margin, k_used, imp) in pos_rows:
                context = f"{tournament} | {stage} | {match_type}"
                print(f"    +{delta:.2f}  #{match_id} {context} vs {opp} (exp {exp:.2f}, act {act:.2f}, margin {margin}, k {k_used:.2f}, imp {imp:.2f})")
            print("  Negative:")
            for (match_id, tournament, stage, match_type, match_name, t, opp, delta, exp, act, margin, k_used, imp) in neg_rows:
                context = f"{tournament} | {stage} | {match_type}"
                print(f"    {delta:.2f}  #{match_id} {context} vs {opp} (exp {exp:.2f}, act {act:.2f}, margin {margin}, k {k_used:.2f}, imp {imp:.2f})")
        else:
            cur.execute(
                """
                SELECT h.match_id, m.tournament, m.stage, m.match_type, m.match_name,
                       h.team, h.opponent, (h.post_rating - h.pre_rating) AS delta, h.expected, h.actual, h.margin, h.k_used, h.importance
                FROM Elo_History h
                LEFT JOIN Matches m ON m.match_id = h.match_id
                ORDER BY delta DESC
                LIMIT ?
                """,
                (args.limit,),
            )
            pos_rows = cur.fetchall()
            cur.execute(
                """
                SELECT h.match_id, m.tournament, m.stage, m.match_type, m.match_name,
                       h.team, h.opponent, (h.post_rating - h.pre_rating) AS delta, h.expected, h.actual, h.margin, h.k_used, h.importance
                FROM Elo_History h
                LEFT JOIN Matches m ON m.match_id = h.match_id
                ORDER BY delta ASC
                LIMIT ?
                """,
                (args.limit,),
            )
            neg_rows = cur.fetchall()
            print(f"\nLargest swings overall (top {args.limit}):")
            print("  Positive:")
            for (match_id, tournament, stage, match_type, match_name, t, opp, delta, exp, act, margin, k_used, imp) in pos_rows:
                context = f"{tournament} | {stage} | {match_type}"
                print(f"    +{delta:.2f}  #{match_id} {t} vs {opp} — {context} (exp {exp:.2f}, act {act:.2f}, margin {margin}, k {k_used:.2f}, imp {imp:.2f})")
            print("  Negative:")
            for (match_id, tournament, stage, match_type, match_name, t, opp, delta, exp, act, margin, k_used, imp) in neg_rows:
                context = f"{tournament} | {stage} | {match_type}"
                print(f"    {delta:.2f}  #{match_id} {t} vs {opp} — {context} (exp {exp:.2f}, act {act:.2f}, margin {margin}, k {k_used:.2f}, imp {imp:.2f})")

    conn.close()
