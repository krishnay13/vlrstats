import sqlite3
import json
import os


# Set up the SQLite database
def setup_database():
    base_dir = os.path.dirname(__file__)
    db_path = os.path.abspath(os.path.join(base_dir, '..', 'valorant_esports.db'))
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop existing tables to reset the database
    tables_to_drop = ['Matches', 'Maps', 'Players', 'Player_Stats', 'Teams',
                      'Scores', 'Overview', 'MapScores', 'MapsPlayed']
    for table in tables_to_drop:
        cursor.execute(f'DROP TABLE IF EXISTS {table}')

    # Create Matches table with 10 player stat IDs (match totals)
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

    # Create Maps table with 10 player stat IDs (map totals)
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

    # Create Players table (unchanged)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Players (
        player_id INTEGER PRIMARY KEY,
        player_name TEXT,
        team_name TEXT
    )
    ''')

    # Create Player_Stats table (unchanged)
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

    # Create Teams table with a UNIQUE constraint on team_name
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
    
    # New: External scraper format tables
    # Scores table (tournament-level match scores)
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

    # Overview table (per-map player stats)
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

    # New: Per-map team score totals
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

    # New: Maps played per match
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


# Database insertion functions
def insert_match(cursor, team1_name, team2_name, team1_score, team2_score, map1_id, map2_id, map3_id, match_stat_ids):
    cursor.execute('''
    INSERT INTO Matches (team1_name, team2_name, team1_score, team2_score, map1_id, map2_id, map3_id, p1_stat_id,
                         p2_stat_id, p3_stat_id, p4_stat_id, p5_stat_id, p6_stat_id, p7_stat_id, p8_stat_id,
                         p9_stat_id, p10_stat_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (team1_name, team2_name, team1_score, team2_score, map1_id, map2_id, map3_id, *match_stat_ids))
    return cursor.lastrowid


def insert_map(cursor, match_id, map_name, team1_name, team2_name, team1_score, team2_score, map_stat_ids):
    cursor.execute('''
    INSERT INTO Maps (match_id, map_name, team1_name, team2_name, team1_score, team2_score, p1_stat_id, p2_stat_id,
                      p3_stat_id, p4_stat_id, p5_stat_id, p6_stat_id, p7_stat_id, p8_stat_id, p9_stat_id, p10_stat_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (match_id, map_name, team1_name, team2_name, team1_score, team2_score, *map_stat_ids))
    return cursor.lastrowid


def get_or_insert_team(cursor, team_name, player_ids):
    cursor.execute('SELECT team_id FROM Teams WHERE team_name = ?', (team_name,))
    result = cursor.fetchone()
    if result:
        # Team exists, update player IDs if necessary
        team_id = result[0]
        cursor.execute('''
        UPDATE Teams SET player1_id = ?, player2_id = ?, player3_id = ?, player4_id = ?, player5_id = ?
        WHERE team_id = ?
        ''', (player_ids[0], player_ids[1], player_ids[2], player_ids[3], player_ids[4], team_id))
        return team_id
    else:
        # Team does not exist, insert new team
        cursor.execute('''
        INSERT INTO Teams (team_name, player1_id, player2_id, player3_id, player4_id, player5_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (team_name, *player_ids))
        return cursor.lastrowid


def get_or_insert_player(cursor, player_name, team_name):
    cursor.execute('SELECT player_id FROM Players WHERE player_name = ?', (player_name,))
    result = cursor.fetchone()
    if result is None:
        cursor.execute('INSERT INTO Players (player_name, team_name) VALUES (?, ?)', (player_name, team_name))
        return cursor.lastrowid
    else:
        # Update team name if different
        player_id = result[0]
        cursor.execute('UPDATE Players SET team_name = ? WHERE player_id = ?', (team_name, player_id))
        return player_id


def insert_player_stats(cursor, player_id, match_id, map_id, player_stats):
    cursor.execute('''
    INSERT INTO Player_Stats (player_id, match_id, map_id, kills, deaths, assists, acs, rating, agent, plus_minus,
                              kast, adr, hs_percentage, fk, fd, f_plus_minus)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (player_id, match_id, map_id, player_stats['kills'], player_stats['deaths'], player_stats['assists'],
          player_stats['acs'], player_stats['rating'], player_stats['agent'], player_stats['plus_minus'],
          player_stats['kast'], player_stats['adr'], player_stats['hs_percentage'], player_stats['fk'],
          player_stats['fd'], player_stats['f_plus_minus']))
    return cursor.lastrowid


if __name__ == "__main__":
    conn = setup_database()
    conn.close()
