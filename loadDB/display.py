import sqlite3
from datetime import datetime, timedelta
from typing import Optional
from .config import DB_PATH


def _conn(db_path: str | None = None) -> sqlite3.Connection:
    """Get database connection."""
    return sqlite3.connect(db_path or DB_PATH)


def _parse_date_range(date_range: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
    """
    Parse date range string into start and end dates.
    
    Supported formats:
    - "2024" - entire year 2024
    - "2025" - entire year 2025
    - "last-3-months" - last 3 months from today
    - "last-6-months" - last 6 months from today
    - "all-time" or None - no date filtering
    
    Args:
        date_range: Date range string
    
    Returns:
        Tuple of (start_date, end_date) in YYYY-MM-DD format, or (None, None) for all-time
    """
    if not date_range or date_range.lower() == 'all-time':
        return None, None
    
    today = datetime.now()
    
    if date_range == "2024":
        return "2024-01-01", "2024-12-31"
    elif date_range == "2025":
        return "2025-01-01", "2025-12-31"
    elif date_range.lower() == "last-3-months":
        start = today - timedelta(days=90)
        return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    elif date_range.lower() == "last-6-months":
        start = today - timedelta(days=180)
        return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    
    return None, None


def top_teams(n: int = 20, date_range: Optional[str] = None):
    """
    Get top teams by Elo rating, optionally filtered by date range.
    
    If date_range is specified, computes Elo ratings only from matches in that range.
    Otherwise, uses the pre-computed Elo_Current table.
    
    Args:
        n: Number of top teams to return
        date_range: Optional date range filter (see _parse_date_range for formats)
    
    Returns:
        List of tuples (team, rating, matches)
    """
    start_date, end_date = _parse_date_range(date_range)
    
    if start_date and end_date:
        return _top_teams_by_date_range(n, start_date, end_date)
    
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT team, rating, matches FROM Elo_Current ORDER BY rating DESC LIMIT ?", (n,))
    rows = cur.fetchall()
    conn.close()
    return rows


def _top_teams_by_date_range(n: int, start_date: str, end_date: str):
    """
    Compute and return top teams based on Elo ratings from matches in date range.
    
    Args:
        n: Number of top teams to return
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        List of tuples (team, rating, matches)
    """
    from .elo import _compute_elo_ratings
    
    ratings, games_played = _compute_elo_ratings(start_date, end_date)
    
    top_list = sorted(ratings.items(), key=lambda x: x[1], reverse=True)[:n]
    return [(team, rating, games_played.get(team, 0)) for team, rating in top_list]


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
