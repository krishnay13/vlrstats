import sqlite3
from .config import DB_PATH


def get_conn(db_path: str | None = None) -> sqlite3.Connection:
    return sqlite3.connect(db_path or DB_PATH)


def ensure_matches_columns(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(Matches)")
    cols = {r[1] for r in cur.fetchall()}
    if 'match_ts_utc' not in cols:
        cur.execute("ALTER TABLE Matches ADD COLUMN match_ts_utc TEXT")
        conn.commit()
    if 'match_date' not in cols:
        cur.execute("ALTER TABLE Matches ADD COLUMN match_date TEXT")
        conn.commit()
    # Migrate tournament_type to match_type if it exists
    if 'tournament_type' in cols and 'match_type' in cols:
        # Copy tournament_type values to match_type where match_type is empty or old format
        cur.execute("""
            UPDATE Matches 
            SET match_type = tournament_type 
            WHERE (match_type IS NULL OR match_type = '' OR match_type NOT IN ('VCT', 'VCL', 'OFFSEASON', 'SHOWMATCH'))
            AND tournament_type IS NOT NULL
        """)
        conn.commit()
        # Drop tournament_type column after migration
        # Note: SQLite doesn't support DROP COLUMN directly, so we'll leave it for now
        # but use match_type going forward


def upsert_match(conn: sqlite3.Connection, row: tuple) -> None:
    # Handle both old format (12 fields) and new format (13 fields with match_type classification)
    # match_type now stores VCT/VCL/OFFSEASON/SHOWMATCH instead of parsed match name part
    if len(row) == 12:
        # Old format - match_type is the 4th field (index 3) and contains parsed match name part
        # We'll keep it as is for backward compatibility
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
    else:
        # New format with match_type classification (13 fields)
        # match_type field now contains VCT/VCL/OFFSEASON/SHOWMATCH
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
