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
    
    Always inserts maps even if scores are None, to ensure consistency.
    
    Args:
        conn: Database connection
        maps: List of tuples (match_id, game_id, map_name, team_a_score, team_b_score)
    
    Returns:
        Dictionary mapping (match_id, game_id) to map database id
    """
    cur = conn.cursor()
    lookup: dict[tuple[int, str], int] = {}
    for match_id, game_id, map_name, ta_score, tb_score in maps:
        # Ensure map_name is not None or empty
        if not map_name or map_name == '':
            map_name = 'Unknown'
        
        # Validate scores are within reasonable range
        if ta_score is not None and (ta_score < 0 or ta_score > 13):
            ta_score = None
        if tb_score is not None and (tb_score < 0 or tb_score > 13):
            tb_score = None
        
        cur.execute(
            """
            INSERT INTO Maps (match_id, game_id, map, team_a_score, team_b_score)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(match_id, game_id) DO UPDATE SET
                map=COALESCE(excluded.map, Maps.map),
                team_a_score=COALESCE(excluded.team_a_score, Maps.team_a_score),
                team_b_score=COALESCE(excluded.team_b_score, Maps.team_b_score)
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
    
    Handles missing map_id by looking it up, and validates stat values.
    
    Args:
        conn: Database connection
        stats: List of tuples (match_id, game_id, player, team, agent, rating, acs, kills, deaths, assists)
        map_lookup: Dictionary mapping (match_id, game_id) to map database id
    """
    cur = conn.cursor()
    for match_id, game_id, player, team, agent, rating, acs, kills, deaths, assists in stats:
        # Skip if player name is missing
        if not player or player == '' or player == 'Unknown':
            continue
        
        # Look up map_id
        map_id = map_lookup.get((match_id, game_id))
        if map_id is None:
            cur.execute("SELECT id FROM Maps WHERE match_id = ? AND game_id = ?", (match_id, game_id))
            row = cur.fetchone()
            map_id = int(row[0]) if row else None
        
        # If still no map_id, try to create/find the map
        if map_id is None:
            # Try to insert a placeholder map if it doesn't exist
            cur.execute(
                """
                INSERT OR IGNORE INTO Maps (match_id, game_id, map, team_a_score, team_b_score)
                VALUES (?, ?, 'Unknown', NULL, NULL)
                """,
                (match_id, game_id),
            )
            cur.execute("SELECT id FROM Maps WHERE match_id = ? AND game_id = ?", (match_id, game_id))
            row = cur.fetchone()
            map_id = int(row[0]) if row else None
        
        # Skip if we still don't have a map_id
        if map_id is None:
            continue
        
        # Validate and clean stat values
        team = team or 'Unknown'
        agent = agent or 'Unknown'
        rating = max(0.0, min(5.0, rating)) if rating is not None else 0.0
        acs = max(0, min(500, int(acs))) if acs is not None else 0
        kills = max(0, int(kills)) if kills is not None else 0
        deaths = max(0, int(deaths)) if deaths is not None else 0
        assists = max(0, int(assists)) if assists is not None else 0
        
        cur.execute(
            """
            INSERT INTO Player_Stats (match_id, map_id, game_id, player, team, agent, rating, acs, kills, deaths, assists)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(match_id, map_id, player) DO UPDATE SET
                team=COALESCE(excluded.team, Player_Stats.team),
                agent=COALESCE(excluded.agent, Player_Stats.agent),
                rating=COALESCE(excluded.rating, Player_Stats.rating),
                acs=COALESCE(excluded.acs, Player_Stats.acs),
                kills=COALESCE(excluded.kills, Player_Stats.kills),
                deaths=COALESCE(excluded.deaths, Player_Stats.deaths),
                assists=COALESCE(excluded.assists, Player_Stats.assists)
            """,
            (match_id, map_id, game_id, player, team, agent, rating, acs, kills, deaths, assists),
        )
