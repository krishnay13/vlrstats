import sqlite3
import os


def setup_database():
    base_dir = os.path.dirname(__file__)
    db_path = os.path.abspath(os.path.join(base_dir, '..', 'valorant_esports.db'))
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables_to_drop = ['Matches', 'Maps', 'Players', 'Player_Stats', 'Teams',
                      'Scores', 'Overview', 'MapScores', 'MapsPlayed']
    for table in tables_to_drop:
        cursor.execute(f'DROP TABLE IF EXISTS {table}')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Matches (
        match_id INTEGER PRIMARY KEY,
        team1_name TEXT,
        team2_name TEXT,
        team1_score INTEGER,
        team2_score INTEGER,
        map1_id INTEGER,
        map2_id INTEGER,
        map3_id INTEGER,
        p1_stat_id INTEGER,
        p2_stat_id INTEGER,
        p3_stat_id INTEGER,
        p4_stat_id INTEGER,
        p5_stat_id INTEGER,
        p6_stat_id INTEGER,
        p7_stat_id INTEGER,
        p8_stat_id INTEGER,
        p9_stat_id INTEGER,
        p10_stat_id INTEGER
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Maps (
        map_id INTEGER PRIMARY KEY,
        match_id INTEGER,
        map_name TEXT,
        team1_name TEXT,
        team2_name TEXT,
        team1_score INTEGER,
        team2_score INTEGER,
        p1_stat_id INTEGER,
        p2_stat_id INTEGER,
        p3_stat_id INTEGER,
        p4_stat_id INTEGER,
        p5_stat_id INTEGER,
        p6_stat_id INTEGER,
        p7_stat_id INTEGER,
        p8_stat_id INTEGER,
        p9_stat_id INTEGER,
        p10_stat_id INTEGER
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Players (
        player_id INTEGER PRIMARY KEY,
        player_name TEXT,
        team_name TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Player_Stats (
        stat_id INTEGER PRIMARY KEY,
        player_id INTEGER,
        match_id INTEGER,
        map_id INTEGER,
        kills INTEGER,
        deaths INTEGER,
        assists INTEGER,
        acs INTEGER,
        rating REAL,
        agent TEXT,
        plus_minus TEXT,
        kast TEXT,
        adr INTEGER,
        hs_percentage TEXT,
        fk INTEGER,
        fd INTEGER,
        f_plus_minus TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Teams (
        team_id INTEGER PRIMARY KEY,
        team_name TEXT UNIQUE,
        player1_id INTEGER,
        player2_id INTEGER,
        player3_id INTEGER,
        player4_id INTEGER,
        player5_id INTEGER
    )
    ''')

    conn.commit()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Scores (
        id INTEGER PRIMARY KEY,
        match_id INTEGER,
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
    CREATE TABLE IF NOT EXISTS Overview (
        id INTEGER PRIMARY KEY,
        match_id INTEGER,
        tournament TEXT,
        stage TEXT,
        match_type TEXT,
        match_name TEXT,
        map TEXT,
        player TEXT,
        team TEXT,
        agents TEXT,
        rating REAL,
        average_combat_score INTEGER,
        kills INTEGER,
        deaths INTEGER,
        assists INTEGER,
        kd TEXT,
        kast TEXT,
        adr INTEGER,
        headshot_pct TEXT,
        first_kills INTEGER,
        first_deaths INTEGER,
        fkd TEXT,
        side TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS MapScores (
        id INTEGER PRIMARY KEY,
        match_id INTEGER,
        tournament TEXT,
        stage TEXT,
        match_type TEXT,
        match_name TEXT,
        map TEXT,
        team_a TEXT,
        team_a_score INTEGER,
        team_b TEXT,
        team_b_score INTEGER
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS MapsPlayed (
        id INTEGER PRIMARY KEY,
        match_id INTEGER,
        tournament TEXT,
        stage TEXT,
        match_type TEXT,
        match_name TEXT,
        map TEXT
    )
    ''')

    conn.commit()
    return conn


if __name__ == "__main__":
    conn = setup_database()
    conn.close()
