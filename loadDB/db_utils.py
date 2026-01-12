import sqlite3
from .config import DB_PATH


def get_conn(db_path: str | None = None) -> sqlite3.Connection:
    """
    Get a database connection.
    
    Args:
        db_path: Optional path to database file. If None, uses default from config.
    
    Returns:
        SQLite connection object
    """
    return sqlite3.connect(db_path or DB_PATH)


def ensure_matches_columns(conn: sqlite3.Connection) -> None:
    """
    Ensure Matches table has required columns, adding them if missing.
    
    Also migrates data from tournament_type to match_type if tournament_type exists.
    Note: SQLite doesn't support DROP COLUMN, so tournament_type column remains
    but match_type is used going forward.
    
    Args:
        conn: Database connection
    """
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(Matches)")
    cols = {r[1] for r in cur.fetchall()}
    if 'match_ts_utc' not in cols:
        cur.execute("ALTER TABLE Matches ADD COLUMN match_ts_utc TEXT")
        conn.commit()
    if 'match_date' not in cols:
        cur.execute("ALTER TABLE Matches ADD COLUMN match_date TEXT")
        conn.commit()
    if 'tournament_type' in cols and 'match_type' in cols:
        cur.execute("""
            UPDATE Matches 
            SET match_type = tournament_type 
            WHERE (match_type IS NULL OR match_type = '' OR match_type NOT IN ('VCT', 'VCL', 'OFFSEASON', 'SHOWMATCH'))
            AND tournament_type IS NOT NULL
        """)
        conn.commit()


def upsert_match(conn: sqlite3.Connection, row: tuple) -> None:
    """
    Insert or update a match record in the database.
    
    Handles both old format (12 fields) and new format (12 fields with match_type classification).
    The match_type field stores VCT/VCL/OFFSEASON/SHOWMATCH classification.
    
    Args:
        conn: Database connection
        row: Tuple with match data (match_id, tournament, stage, match_type, match_name,
             team_a, team_b, team_a_score, team_b_score, match_result, match_ts_utc, match_date)
    """
    sql = (
        """
        INSERT INTO Matches (
            match_id, tournament, stage, match_type, match_name,
            team_a, team_b, team_a_score, team_b_score, match_result, match_ts_utc, match_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(match_id) DO UPDATE SET
            tournament=excluded.tournament,
            stage=excluded.stage,
            match_type=COALESCE(excluded.match_type, match_type),
            match_name=excluded.match_name,
            team_a=excluded.team_a,
            team_b=excluded.team_b,
            team_a_score=excluded.team_a_score,
            team_b_score=excluded.team_b_score,
            match_result=excluded.match_result,
            match_ts_utc=COALESCE(excluded.match_ts_utc, match_ts_utc),
            match_date=COALESCE(excluded.match_date, match_date)
        """
    )
    conn.execute(sql, row)


def upsert_maps(conn: sqlite3.Connection, maps: list[tuple]) -> dict[tuple[int, str], int]:
    """
    Insert or update map records and return a lookup dictionary.
    
    Args:
        conn: Database connection
        maps: List of tuples (match_id, game_id, map_name, team_a_score, team_b_score)
    
    Returns:
        Dictionary mapping (match_id, game_id) to map database id
    """
    cur = conn.cursor()
    lookup: dict[tuple[int, str], int] = {}
    for match_id, game_id, map_name, ta_score, tb_score in maps:
        cur.execute(
            """
            INSERT INTO Maps (match_id, game_id, map, team_a_score, team_b_score)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(match_id, game_id) DO UPDATE SET
                map=excluded.map,
                team_a_score=excluded.team_a_score,
                team_b_score=excluded.team_b_score
            """,
            (match_id, game_id, map_name, ta_score, tb_score),
        )
        cur.execute("SELECT id FROM Maps WHERE match_id = ? AND game_id = ?", (match_id, game_id))
        row = cur.fetchone()
        if row:
            lookup[(match_id, game_id)] = int(row[0])
    return lookup


def upsert_player_stats(conn: sqlite3.Connection, stats: list[tuple], map_lookup: dict[tuple[int, str], int]) -> None:
    """
    Insert or update player statistics records.
    
    Args:
        conn: Database connection
        stats: List of tuples (match_id, game_id, player, team, agent, rating, acs, kills, deaths, assists)
        map_lookup: Dictionary mapping (match_id, game_id) to map database id
    """
    cur = conn.cursor()
    for match_id, game_id, player, team, agent, rating, acs, kills, deaths, assists in stats:
        map_id = map_lookup.get((match_id, game_id))
        if map_id is None:
            cur.execute("SELECT id FROM Maps WHERE match_id = ? AND game_id = ?", (match_id, game_id))
            row = cur.fetchone()
            map_id = int(row[0]) if row else None
        cur.execute(
            """
            INSERT INTO Player_Stats (match_id, map_id, game_id, player, team, agent, rating, acs, kills, deaths, assists)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(match_id, map_id, player) DO UPDATE SET
                team=excluded.team,
                agent=excluded.agent,
                rating=excluded.rating,
                acs=excluded.acs,
                kills=excluded.kills,
                deaths=excluded.deaths,
                assists=excluded.assists
            """,
            (match_id, map_id, game_id, player, team, agent, rating, acs, kills, deaths, assists),
        )
