import sqlite3
from datetime import date
import json


# Set up the SQLite database
def setup_database():
    conn = sqlite3.connect('valorant_esports.db')
    cursor = conn.cursor()


    tables_to_drop = [
        'Maps', 'Matches', 'PlayerStats', 'Player_Matches',
        'Player_Stats', 'Players', 'Team_Matches', 'Team_Stats', 'Teams'
    ]

    for table in tables_to_drop:
        cursor.execute(f'DROP TABLE IF EXISTS {table}')

    # Create tables
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
        match_stats TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Maps (
        map_id INTEGER PRIMARY KEY,
        team1_name TEXT,
        team2_name TEXT,
        team1_score INTEGER,
        team2_score INTEGER,
        map_name TEXT,
        map_stats TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Teams (
        team_id INTEGER PRIMARY KEY,
        team_name TEXT UNIQUE,
        player_ids TEXT,
        avg_kpr REAL,
        avg_kpg REAL,
        avg_dpr REAL,
        avg_dpg REAL,
        avg_fb_fd_per_game REAL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Players (
        player_id INTEGER PRIMARY KEY,
        player_name TEXT,
        agents_kpg TEXT,
        avg_kpg REAL,
        avg_fbp REAL,
        full_avg_stats TEXT
    )
    ''')

    # Save (commit) the changes
    conn.commit()
    return conn


# Database insertion functions
def insert_match(cursor, team1_name, team2_name, team1_score, team2_score, map1_id, map2_id, map3_id, match_stats):
    cursor.execute('''
    INSERT INTO Matches (team1_name, team2_name, team1_score, team2_score, map1_id, map2_id, map3_id, match_stats)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (team1_name, team2_name, team1_score, team2_score, map1_id, map2_id, map3_id, json.dumps(match_stats)))
    return cursor.lastrowid


def insert_map(cursor, team1_name, team2_name, team1_score, team2_score, map_name, map_stats):
    cursor.execute('''
    INSERT INTO Maps (team1_name, team2_name, team1_score, team2_score, map_name, map_stats)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (team1_name, team2_name, team1_score, team2_score, map_name, json.dumps(map_stats)))
    return cursor.lastrowid


def get_or_insert_team(cursor, team_name):
    cursor.execute('SELECT team_id FROM Teams WHERE team_name = ?', (team_name,))
    result = cursor.fetchone()
    if result is None:
        cursor.execute('INSERT INTO Teams (team_name) VALUES (?)', (team_name,))
        return cursor.lastrowid
    else:
        return result[0]


def insert_team(cursor, team_name, player_ids, avg_kpr, avg_kpg, avg_dpr, avg_dpg, avg_fb_fd_per_game):
    cursor.execute('''
    INSERT INTO Teams (team_name, player_ids, avg_kpr, avg_kpg, avg_dpr, avg_dpg, avg_fb_fd_per_game)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (team_name, json.dumps(player_ids), avg_kpr, avg_kpg, avg_dpr, avg_dpg, avg_fb_fd_per_game))


def get_or_insert_player(cursor, player_name):
    cursor.execute('SELECT player_id FROM Players WHERE player_name = ?', (player_name,))
    result = cursor.fetchone()
    if result is None:
        cursor.execute('INSERT INTO Players (player_name) VALUES (?)', (player_name,))
        return cursor.lastrowid
    else:
        return result[0]


def insert_player(cursor, player_name, agents_kpg, avg_kpg, avg_fbp, full_avg_stats):
    cursor.execute('''
    INSERT INTO Players (player_name, agents_kpg, avg_kpg, avg_fbp, full_avg_stats)
    VALUES (?, ?, ?, ?, ?)
    ''', (player_name, json.dumps(agents_kpg), avg_kpg, avg_fbp, json.dumps(full_avg_stats)))


# Example usage
def main():
    conn = setup_database()
    cursor = conn.cursor()

    # Sample data
    team1_name = "FUT Esports"
    team2_name = "FNATIC"
    team1_score = 2
    team2_score = 1
    match_stats = []

    map1_stats = [
        {'player_name': 'yetujey', 'team': 'FUT', 'agent': 'Viper', 'rating': 0.0, 'acs': 210, 'kills': 13,
         'deaths': 14, 'assists': 1, 'plus_minus': '-1', 'kast': '', 'adr': 143, 'hs_percentage': '39%', 'fk': 3,
         'fd': 2, 'f_plus_minus': '+1'},
        # Add other players' stats for map1
    ]
    map2_stats = [
        # Add players' stats for map2
    ]
    map3_stats = [
        # Add players' stats for map3
    ]

    map1_id = insert_map(cursor, team1_name, team2_name, 5, 13, "Split", map1_stats)
    map2_id = insert_map(cursor, team1_name, team2_name, 13, 8, "Lotus", map2_stats)
    map3_id = insert_map(cursor, team1_name, team2_name, 13, 3, "Ascent", map3_stats)

    match_id = insert_match(cursor, team1_name, team2_name, team1_score, team2_score, map1_id, map2_id, map3_id,
                            match_stats)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
