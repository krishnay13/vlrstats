import sqlite3
from .config import DB_PATH


def _conn(db_path: str | None = None) -> sqlite3.Connection:
    return sqlite3.connect(db_path or DB_PATH)


def top_teams(n: int = 20):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT team, rating, matches FROM Elo_Current ORDER BY rating DESC LIMIT ?", (n,))
    rows = cur.fetchall()
    conn.close()
    return rows


def top_players(n: int = 20):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT player, team, rating, matches FROM Player_Elo_Current ORDER BY rating DESC LIMIT ?", (n,))
    rows = cur.fetchall()
    conn.close()
    return rows


def team_history(team: str):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT h.match_id, m.tournament, m.stage, m.match_type, h.opponent, h.pre_rating, h.post_rating
        FROM Elo_History h LEFT JOIN Matches m ON m.match_id = h.match_id
        WHERE LOWER(h.team) = LOWER(?) ORDER BY h.match_id ASC
        """,
        (team,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def player_history(player: str):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT match_id, team, opponent_team, pre_rating, post_rating
        FROM Player_Elo_History WHERE LOWER(player) = LOWER(?) ORDER BY match_id ASC
        """,
        (player,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows
