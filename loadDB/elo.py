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
    MOV_BASE,
    MOV_RDIFF_SCALE,
    ROUND_MARGIN_DIVISOR,
    ROUND_MARGIN_MIN,
    ROUND_MARGIN_MAX,
    ROUND_MARGIN_MAPS_BONUS,
    IMP_CHAMPIONS,
    IMP_MASTERS_BASE,
    IMP_MASTERS_BANGKOK,
    IMP_MASTERS_TORONTO,
    IMP_REGIONAL,
    IMP_VCL,
    IMP_OFFSEASON,
    IMP_SHOWMATCH,
    IMP_MATCH_GRAND_FINAL,
    IMP_MATCH_FINALS_UPPER_LOWER,
    IMP_MATCH_SEMIFINAL,
    IMP_MATCH_QUARTERFINAL,
    IMP_MATCH_PLAYOFF,
    IMP_MATCH_ELIM_DECIDER,
    IMP_MATCH_GROUP_OR_SWISS,
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
)
from .normalizers.team import normalize_team

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
    mt = (match_type or '').upper()

    # Tournament category (competition tier)
    if 'champions' in t:
        t_w = IMP_CHAMPIONS
    elif 'masters' in t:
        if 'bangkok' in t:
            t_w = IMP_MASTERS_BANGKOK
        elif 'toronto' in t:
            t_w = IMP_MASTERS_TORONTO
        else:
            t_w = IMP_MASTERS_BASE
    elif 'vcl' in t or 'challengers' in t:
        t_w = IMP_VCL
    else:
        # Default to regional / domestic VCT weight
        t_w = IMP_REGIONAL

    # Adjust for explicit match_type tier when available
    if mt == 'OFFSEASON':
        t_w *= IMP_OFFSEASON
    elif mt == 'SHOWMATCH':
        t_w *= IMP_SHOWMATCH
    # VCL is already captured above via tournament name

    # Bracket / match context weighting.
    # Use stage (and fall back to tournament text) to infer context.
    ctx = f"{s} {t}".lower()
    if 'grand final' in ctx:
        m_w = IMP_MATCH_GRAND_FINAL
    elif 'lower final' in ctx or 'upper final' in ctx:
        m_w = IMP_MATCH_FINALS_UPPER_LOWER
    elif 'semifinal' in ctx or 'semi-final' in ctx:
        m_w = IMP_MATCH_SEMIFINAL
    elif 'quarterfinal' in ctx or 'quarter-final' in ctx:
        m_w = IMP_MATCH_QUARTERFINAL
    elif 'playoff' in ctx:
        m_w = IMP_MATCH_PLAYOFF
    elif 'elimination' in ctx or 'decider' in ctx:
        m_w = IMP_MATCH_ELIM_DECIDER
    elif 'group stage' in ctx or 'swiss' in ctx or 'week' in ctx:
        m_w = IMP_MATCH_GROUP_OR_SWISS
    else:
        m_w = 1.0
    return t_w * m_w


def expected_score(r_a: float, r_b: float) -> float:
    return 1.0 / (1.0 + math.pow(10.0, (r_b - r_a) / 400.0))


def mov_multiplier(margin: int, rdiff: float) -> float:
    """
    Margin-of-victory multiplier for Elo updates.

    Classic form (basketball Elo):
        ln(1 + margin) * MOV_BASE / (|rdiff| * MOV_RDIFF_SCALE + MOV_BASE)

    Tuned via MOV_* constants in config.
    """
    effective_margin = max(1, margin)
    numerator = math.log(1 + effective_margin) * MOV_BASE
    denominator = abs(rdiff) * MOV_RDIFF_SCALE + MOV_BASE
    return numerator / denominator if denominator > 0 else 1.0


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
        # Scale down and clamp to a sensible range, with optional series-length bonus.
        scaled = avg_round_margin / float(ROUND_MARGIN_DIVISOR)
        if ROUND_MARGIN_MAPS_BONUS > 0.0:
            scaled *= 1.0 + ROUND_MARGIN_MAPS_BONUS * max(0, int(maps_played) - 1)
        return float(
            max(
                ROUND_MARGIN_MIN,
                min(ROUND_MARGIN_MAX, scaled),
            )
        )
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


def compute_elo(
    save: bool = False,
    top: int = 20,
    start_date: str | None = None,
    end_date: str | None = None,
    recency_half_life: float | None = None,
    delta_summary: bool = False,
):
    """
    Compute Elo ratings from matches in the database.
    
    Args:
        save: If True, save Elo history and current ratings to database
        top: Number of top teams to display
        start_date: Optional start date filter (YYYY-MM-DD format)
        end_date: Optional end date filter (YYYY-MM-DD format)
    """
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"DB not found at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Build query with optional date filtering
    query = """
        SELECT match_id, tournament, stage, match_type, match_name, team_a, team_b, team_a_score, team_b_score
        FROM Matches
        WHERE team_a IS NOT NULL AND team_b IS NOT NULL
    """
    params = []
    
    if start_date or end_date:
        date_conditions = []
        if start_date:
            date_conditions.append("(match_date >= ? OR (match_date IS NULL AND match_ts_utc >= ?))")
            params.extend([start_date, start_date])
        if end_date:
            date_conditions.append("(match_date <= ? OR (match_date IS NULL AND match_ts_utc <= ?))")
            params.extend([end_date, end_date + "T23:59:59Z"])
        
        if date_conditions:
            query += " AND " + " AND ".join(date_conditions)
    
    query += """
        ORDER BY
          CASE WHEN match_date IS NOT NULL AND match_date <> '' THEN 0 ELSE 1 END,
          match_date ASC,
          match_id ASC
    """
    
    cur.execute(query, params)
    matches = cur.fetchall()

    ratings = defaultdict(lambda: START_ELO)
    games_played = defaultdict(int)
    history_rows = []
    # Player Elo tracking
    player_ratings = defaultdict(lambda: PLAYER_START_ELO)
    player_games = defaultdict(int)
    player_history_rows = []
    player_teams: dict[str, str | None] = {}

    total_matches = len(matches)
    per_team_deltas: list[float] = []

    for idx, (match_id, tournament, stage, match_type, match_name, ta, tb, ta_score, tb_score) in enumerate(matches):
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

            # Optional recency weighting: downweight older matches relative to newer ones.
            if recency_half_life and recency_half_life > 0 and total_matches > 0:
                age = float(total_matches - idx - 1)
                # Each half_life worth of age halves the effective K
                recency_factor = 0.5 ** (age / recency_half_life)
                k_eff *= recency_factor

            # Update team ratings only when we have a known result
            new_ra = ra
            new_rb = rb
            if team_update:
                delta_a = k_eff * (sa - exp_a)
                delta_b = k_eff * (sb - exp_b)
                new_ra = ra + delta_a
                new_rb = rb + delta_b
                per_team_deltas.extend([delta_a, delta_b])

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

    if delta_summary and per_team_deltas:
        abs_deltas = [abs(d) for d in per_team_deltas]
        abs_deltas.sort()
        n = len(abs_deltas)
        avg_delta = sum(abs_deltas) / float(n)
        p95_idx = max(0, int(0.95 * n) - 1)
        p95_delta = abs_deltas[p95_idx]
        max_delta = abs_deltas[-1]
        print("\nElo delta summary (per team per match):")
        print(f"  Samples      : {n}")
        print(f"  Avg |Δrating|: {avg_delta:.2f}")
        print(f"  95th pct     : {p95_delta:.2f}")
        print(f"  Max |Δrating|: {max_delta:.2f}")

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

        # Most recent team per player from Player_Stats (not most frequent)
        # This ensures players who changed teams show up with their current team
        cur.execute(
            """
            SELECT player, team, match_id
            FROM Player_Stats
            WHERE player IS NOT NULL AND team IS NOT NULL
            ORDER BY match_id DESC
            """
        )
        player_team_rows = cur.fetchall()
        most_team: dict[str, str] = {}
        for player, team, match_id in player_team_rows:
            if player and player not in most_team:
                most_team[player] = normalize_team(team)

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
            team = most_team.get(p)
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


def compute_elo_snapshots():
    """
    Compute and store ELO snapshots for fixed date ranges (2024, 2025) and 
    recalculate for current year (2026) and all-time.
    Automatically called after ingestion to keep current year and all-time updated.
    """
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"DB not found at {DB_PATH}")

    # Define date ranges: fixed years and current year
    date_ranges = [
        ('2024', '2024-01-01', '2024-12-31'),
        ('2025', '2025-01-01', '2025-12-31'),
        ('2026', '2026-01-01', '2026-12-31'),
        (None, None, None),  # all-time
    ]

    for range_name, start_date, end_date in date_ranges:
        print(f"\nComputing ELO snapshot for {range_name or 'all-time'}...")
        
        # Call compute_elo with save=True to populate Elo_Current and Player_Elo_Current
        compute_elo(save=True, top=5, start_date=start_date, end_date=end_date)
        
        # Now copy from Elo_Current and Player_Elo_Current to snapshot tables
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        if range_name:
            # Create/update team snapshot table for this year
            team_table = f"Elo_{range_name}"
            cur.execute(f"DROP TABLE IF EXISTS {team_table}")
            cur.execute(f"""
                CREATE TABLE {team_table} AS
                SELECT team, rating, matches FROM Elo_Current
            """)
            
            # Create/update player snapshot table for this year
            player_table = f"Player_Elo_{range_name}"
            cur.execute(f"DROP TABLE IF EXISTS {player_table}")
            cur.execute(f"""
                CREATE TABLE {player_table} AS
                SELECT player, team, rating, matches, last_match_id FROM Player_Elo_Current
            """)
            print(f"  ✓ Snapshot tables {team_table} and {player_table} created")
        else:
            # For all-time, the Current tables are the snapshot (they already have all-time data)
            print("  ✓ All-time ELO stored in Elo_Current and Player_Elo_Current")
        
        conn.commit()
        conn.close()
    
    print("\n✓ ELO snapshots completed successfully!")



def _compute_elo_ratings(start_date: str | None = None, end_date: str | None = None):
    """
    Compute Elo ratings for a date range without saving to database.
    
    Args:
        start_date: Optional start date filter (YYYY-MM-DD format)
        end_date: Optional end date filter (YYYY-MM-DD format)
    
    Returns:
        Tuple of (ratings dict, games_played dict)
    """
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"DB not found at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    query = """
        SELECT match_id, tournament, stage, match_type, match_name, team_a, team_b, team_a_score, team_b_score
        FROM Matches
        WHERE team_a IS NOT NULL AND team_b IS NOT NULL
    """
    params = []
    
    if start_date or end_date:
        date_conditions = []
        if start_date:
            date_conditions.append("(match_date >= ? OR (match_date IS NULL AND match_ts_utc >= ?))")
            params.extend([start_date, start_date])
        if end_date:
            date_conditions.append("(match_date <= ? OR (match_date IS NULL AND match_ts_utc <= ?))")
            params.extend([end_date, end_date + "T23:59:59Z"])
        
        if date_conditions:
            query += " AND " + " AND ".join(date_conditions)
    
    query += """
        ORDER BY
          CASE WHEN match_date IS NOT NULL AND match_date <> '' THEN 0 ELSE 1 END,
          match_date ASC,
          match_id ASC
    """
    
    cur.execute(query, params)
    matches = cur.fetchall()

    ratings = defaultdict(lambda: START_ELO)
    games_played = defaultdict(int)

    for match_id, tournament, stage, match_type, match_name, ta, tb, ta_score, tb_score in matches:
        try:
            a = normalize_team(ta)
            b = normalize_team(tb)
            if not a or not b:
                continue

            ra = ratings[a]
            rb = ratings[b]

            roster_a = get_team_roster(cur, match_id, a)
            roster_b = get_team_roster(cur, match_id, b)
            avg_pa = mean([START_ELO for p in roster_a]) if roster_a else START_ELO
            avg_pb = mean([START_ELO for p in roster_b]) if roster_b else START_ELO
            ra_eff = ra + PLAYER_INFLUENCE_BETA * (avg_pa - START_ELO)
            rb_eff = rb + PLAYER_INFLUENCE_BETA * (avg_pb - START_ELO)

            exp_a = expected_score(ra_eff, rb_eff)
            exp_b = 1.0 - exp_a

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
            round_margin = get_round_margin(cur, match_id)
            use_margin = round_margin if round_margin is not None else float(margin)
            mult = mov_multiplier(use_margin, rdiff)
            k_eff = k * imp * mult

            new_ra = ra
            new_rb = rb
            if team_update:
                new_ra = ra + k_eff * (sa - exp_a)
                new_rb = rb + k_eff * (sb - exp_b)

            ratings[a] = new_ra
            ratings[b] = new_rb
            games_played[a] += 1
            games_played[b] += 1
        except Exception as e:
            continue

    conn.close()
    return dict(ratings), dict(games_played)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute Elo ratings from Matches table")
    parser.add_argument("--save", action="store_true", help="Save Elo history and current ratings to DB")
    parser.add_argument("--top", type=int, default=20, help="Number of top teams to display")
    parser.add_argument("--top-players", type=int, default=0, help="Number of top players to display from Player_Elo_Current")
    parser.add_argument(
        "--recency-half-life",
        type=float,
        default=None,
        help="Optional half-life in matches for recency weighting (larger = slower decay, omit to disable)",
    )
    parser.add_argument(
        "--delta-summary",
        action="store_true",
        help="Print summary statistics of Elo rating deltas (per team per match)",
    )
    parser.add_argument("--team", type=str, help="Show Elo history breakdown for a specific team")
    parser.add_argument("--swings", action="store_true", help="Show largest positive/negative Elo swings")
    parser.add_argument("--limit", type=int, default=10, help="Number of swings to display per direction")
    args = parser.parse_args()
    compute_elo(
        save=args.save,
        top=args.top,
        recency_half_life=args.recency_half_life,
        delta_summary=args.delta_summary,
    )

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
