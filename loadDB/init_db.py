import sqlite3
import os


def setup_database():
    base_dir = os.path.dirname(__file__)
    db_path = os.path.abspath(os.path.join(base_dir, '..', 'valorant_esports.db'))
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop all legacy tables and external-format tables
    tables_to_drop = [
        'Matches', 'Maps', 'Player_Stats',
        'Players', 'Teams', 'Scores', 'Overview', 'MapScores', 'MapsPlayed'
    ]
    for table in tables_to_drop:
        cursor.execute(f'DROP TABLE IF EXISTS {table}')

    # Minimal normalized schema
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Matches (
        match_id INTEGER PRIMARY KEY,
        tournament TEXT,
        stage TEXT,
        match_type TEXT,
        match_name TEXT,
        team_a TEXT,
        team_b TEXT,
        team_a_score INTEGER,
        team_b_score INTEGER,
        match_result TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Maps (
        id INTEGER PRIMARY KEY,
        match_id INTEGER,
        game_id TEXT,
        map TEXT,
        team_a_score INTEGER,
        team_b_score INTEGER,
        UNIQUE(match_id, game_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Player_Stats (
        id INTEGER PRIMARY KEY,
        match_id INTEGER,
        map_id INTEGER,
        game_id TEXT,
        player TEXT,
        team TEXT,
        agent TEXT,
        rating REAL,
        acs INTEGER,
        kills INTEGER,
        deaths INTEGER,
        assists INTEGER,
        UNIQUE(match_id, map_id, player)
    )
    ''')

    # Elo rating tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Elo_History (
        id INTEGER PRIMARY KEY,
        match_id INTEGER,
        team TEXT,
        opponent TEXT,
        pre_rating REAL,
        post_rating REAL,
        expected REAL,
        actual REAL,
        margin INTEGER,
        k_used REAL,
        importance REAL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Elo_Current (
        team TEXT PRIMARY KEY,
        rating REAL,
        matches INTEGER,
        last_match_id INTEGER
    )
    ''')

    conn.commit()
    return conn


if __name__ == "__main__":
    conn = setup_database()
    conn.close()
