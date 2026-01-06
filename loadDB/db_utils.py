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


def upsert_match(conn: sqlite3.Connection, row: tuple) -> None:
    sql = (
        """
        INSERT INTO Matches (
            match_id, tournament, stage, match_type, match_name,
            team_a, team_b, team_a_score, team_b_score, match_result, match_ts_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(match_id) DO UPDATE SET
            tournament=excluded.tournament,
            stage=excluded.stage,
            match_type=excluded.match_type,
            match_name=excluded.match_name,
            team_a=excluded.team_a,
            team_b=excluded.team_b,
            team_a_score=excluded.team_a_score,
            team_b_score=excluded.team_b_score,
            match_result=excluded.match_result,
            match_ts_utc=COALESCE(excluded.match_ts_utc, match_ts_utc)
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
