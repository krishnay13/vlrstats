import sqlite3

# Establish a connection to the database
conn = sqlite3.connect('valorant_esports.db')
cursor = conn.cursor()

# Drop existing tables
tables_to_drop = [
    'Matches', 'Teams', 'Maps', 'Team_Stats', 'Players', 'Player_Stats'
]
for table in tables_to_drop:
    cursor.execute(f'DROP TABLE IF EXISTS {table}')

# Create tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS Matches (
    match_id INTEGER PRIMARY KEY,
    match_name TEXT,
    date_played DATE,
    team1_id INTEGER,
    team2_id INTEGER,
    team1_score INTEGER,
    team2_score INTEGER,
    match_winner TEXT,
    FOREIGN KEY (team1_id) REFERENCES Teams (team_id),
    FOREIGN KEY (team2_id) REFERENCES Teams (team_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Teams (
    team_id INTEGER PRIMARY KEY,
    team_name TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Maps (
    map_id INTEGER PRIMARY KEY,
    match_id INTEGER,
    map_name TEXT,
    team1_score INTEGER,
    team2_score INTEGER,
    map_winner TEXT,
    FOREIGN KEY (match_id) REFERENCES Matches (match_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Team_Stats (
    team_stat_id INTEGER PRIMARY KEY,
    match_id INTEGER,
    team_id INTEGER,
    kills INTEGER,
    deaths INTEGER,
    first_bloods INTEGER,
    first_deaths INTEGER,
    FOREIGN KEY (match_id) REFERENCES Matches (match_id),
    FOREIGN KEY (team_id) REFERENCES Teams (team_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Players (
    player_id INTEGER PRIMARY KEY,
    player_name TEXT,
    team_id INTEGER,
    FOREIGN KEY (team_id) REFERENCES Teams (team_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Player_Stats (
    stat_id INTEGER PRIMARY KEY,
    player_id INTEGER,
    map_id INTEGER,
    kills INTEGER,
    deaths INTEGER,
    assists INTEGER,
    acs INTEGER,
    rating REAL,
    agent TEXT,
    FOREIGN KEY (player_id) REFERENCES Players (player_id),
    FOREIGN KEY (map_id) REFERENCES Maps (map_id)
)
''')

# Save (commit) the changes and close the connection
conn.commit()
conn.close()
