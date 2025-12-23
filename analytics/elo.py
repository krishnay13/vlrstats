import math
import sqlite3
from typing import Dict, Tuple, List, Optional


DEFAULT_TEAM_ELO = 1500.0
DEFAULT_PLAYER_ELO = 1500.0


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10.0 ** (-(rating_a - rating_b) / 400.0))


def update_rating(current: float, score: float, expected: float, k: float) -> float:
    return current + k * (score - expected)


class EloEngine:
    def __init__(self, db_path: str = 'valorant_esports.db', team_k: float = 32.0, player_k: float = 24.0):
        self.db_path = db_path
        self.team_k = team_k
        self.player_k = player_k

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def ensure_schema(self):
        con = self._connect()
        cur = con.cursor()

        # Add ELO columns if they do not exist
        def ensure_column(table: str, col: str, col_type: str, default_value: float):
            cur.execute(f"PRAGMA table_info({table})")
            cols = [r[1] for r in cur.fetchall()]
            if col not in cols:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type} DEFAULT {default_value}")

        ensure_column('Teams', 'team_elo', 'REAL', DEFAULT_TEAM_ELO)
        ensure_column('Players', 'player_elo', 'REAL', DEFAULT_PLAYER_ELO)

        # Create history tables
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS EloHistoryTeam (
                id INTEGER PRIMARY KEY,
                match_id INTEGER,
                team_name TEXT,
                elo_pre REAL,
                elo_post REAL,
                k REAL,
                result INTEGER
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS EloHistoryPlayer (
                id INTEGER PRIMARY KEY,
                match_id INTEGER,
                player_id INTEGER,
                team_name TEXT,
                elo_pre REAL,
                elo_post REAL,
                k REAL,
                result INTEGER,
                rating REAL,
                kills INTEGER,
                deaths INTEGER,
                assists INTEGER
            )
            """
        )

        con.commit()
        con.close()

    def _get_current_team_elos(self, cur) -> Dict[str, float]:
        cur.execute("SELECT team_name, COALESCE(team_elo, ?) FROM Teams", (DEFAULT_TEAM_ELO,))
        return {name: float(elo) for name, elo in cur.fetchall()}

    def _get_current_player_elos(self, cur) -> Dict[int, Tuple[str, float]]:
        cur.execute("SELECT player_id, COALESCE(player_elo, ?), COALESCE(team_name,'') FROM Players", (DEFAULT_PLAYER_ELO,))
        # returns {player_id: (team_name, elo)}
        return {int(pid): (tname, float(elo)) for pid, elo, tname in cur.fetchall()}

    def reset_elos(self):
        con = self._connect()
        cur = con.cursor()
        cur.execute("UPDATE Teams SET team_elo = ?", (DEFAULT_TEAM_ELO,))
        cur.execute("UPDATE Players SET player_elo = ?", (DEFAULT_PLAYER_ELO,))
        cur.execute("DELETE FROM EloHistoryTeam")
        cur.execute("DELETE FROM EloHistoryPlayer")
        con.commit()
        con.close()

    def _match_winner(self, team1_score: Optional[int], team2_score: Optional[int]) -> Optional[int]:
        if team1_score is None or team2_score is None:
            return None
        if team1_score > team2_score:
            return 1
        if team2_score > team1_score:
            return 2
        return None

    def recalc_from_history(self):
        con = self._connect()
        cur = con.cursor()

        self.ensure_schema()
        self.reset_elos()

        # iterate matches in insertion order
        cur.execute(
            "SELECT match_id, team1_name, team2_name, team1_score, team2_score FROM Matches ORDER BY match_id ASC"
        )
        matches = cur.fetchall()

        # local caches
        team_elos = self._get_current_team_elos(cur)
        player_elos = self._get_current_player_elos(cur)

        for match_id, t1, t2, s1, s2 in matches:
            # team elos pre
            r1 = team_elos.get(t1, DEFAULT_TEAM_ELO)
            r2 = team_elos.get(t2, DEFAULT_TEAM_ELO)
            exp1 = expected_score(r1, r2)
            exp2 = 1.0 - exp1

            winner = self._match_winner(s1, s2)
            if winner is None:
                continue
            score1 = 1.0 if winner == 1 else 0.0
            score2 = 1.0 - score1

            # update teams
            r1_post = update_rating(r1, score1, exp1, self.team_k)
            r2_post = update_rating(r2, score2, exp2, self.team_k)

            team_elos[t1] = r1_post
            team_elos[t2] = r2_post

            cur.execute("INSERT INTO EloHistoryTeam (match_id, team_name, elo_pre, elo_post, k, result) VALUES (?,?,?,?,?,?)",
                        (match_id, t1, r1, r1_post, self.team_k, int(score1)))
            cur.execute("INSERT INTO EloHistoryTeam (match_id, team_name, elo_pre, elo_post, k, result) VALUES (?,?,?,?,?,?)",
                        (match_id, t2, r2, r2_post, self.team_k, int(score2)))

            # update players using match total stats (map_id IS NULL)
            cur.execute(
                """
                SELECT ps.stat_id, ps.player_id, ps.kills, ps.deaths, ps.assists, ps.rating, p.team_name
                FROM Player_Stats ps
                JOIN Players p ON p.player_id = ps.player_id
                WHERE ps.match_id = ? AND ps.map_id IS NULL
                """,
                (match_id,)
            )
            rows = cur.fetchall()
            if len(rows) == 10:
                # split by team name; if mixed naming occurs, we still update individually
                # compute team-average rating for scaling
                team_ratings: Dict[str, List[float]] = {}
                for _, pid, _, _, _, rating, team_name in rows:
                    team_ratings.setdefault(team_name or '', []).append(float(rating) if rating is not None else 0.0)
                avg_rating: Dict[str, float] = {k: (sum(v) / len(v) if v else 1.0) for k, v in team_ratings.items()}

                for _, pid, kills, deaths, assists, rating, team_name in rows:
                    team_name = team_name or ''
                    pre = player_elos.get(pid, (team_name, DEFAULT_PLAYER_ELO))[1]
                    exp = expected_score(pre, pre)  # neutral baseline; player-vs-field not strictly defined
                    # scale K by personal performance vs team average rating (fallback 1.0)
                    r = float(rating) if rating is not None else 1.0
                    scale = (r / (avg_rating.get(team_name, r or 1.0) or 1.0))
                    k_eff = max(8.0, min(self.player_k * scale, 48.0))
                    res = score1 if team_name and team_name in (t1, t2) and ((team_name == t1 and winner == 1) or (team_name == t2 and winner == 2)) else (1.0 - score1)
                    post = update_rating(pre, res, exp, k_eff)

                    player_elos[pid] = (team_name, post)
                    cur.execute(
                        "INSERT INTO EloHistoryPlayer (match_id, player_id, team_name, elo_pre, elo_post, k, result, rating, kills, deaths, assists)\n                         VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (match_id, pid, team_name, pre, post, k_eff, int(res), float(r) if rating is not None else None,
                         int(kills) if kills is not None else None,
                         int(deaths) if deaths is not None else None,
                         int(assists) if assists is not None else None)
                    )

        # persist latest elos to tables
        for team_name, elo in team_elos.items():
            cur.execute("UPDATE Teams SET team_elo = ? WHERE team_name = ?", (elo, team_name))
        for pid, (team_name, elo) in player_elos.items():
            cur.execute("UPDATE Players SET player_elo = ?, team_name = COALESCE(team_name, ?) WHERE player_id = ?",
                        (elo, team_name, pid))

        con.commit()
        con.close()
