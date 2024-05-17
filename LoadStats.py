from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import sqlite3
from datetime import date
import requests


# Set up the SQLite database
def setup_database():
    conn = sqlite3.connect('valorant_esports.db')
    cursor = conn.cursor()

    # Drop existing tables to reset the database
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

    # Save (commit) the changes
    conn.commit()
    return conn


# Database insertion functions
def get_or_insert_team(cursor, team_name):
    cursor.execute('SELECT team_id FROM Teams WHERE team_name = ?', (team_name,))
    result = cursor.fetchone()
    if result is None:
        cursor.execute('INSERT INTO Teams (team_name) VALUES (?)', (team_name,))
        return cursor.lastrowid
    else:
        return result[0]


def insert_match(cursor, match_name, date_played, team1_name, team2_name, team1_score, team2_score, match_winner):
    team1_id = get_or_insert_team(cursor, team1_name)
    team2_id = get_or_insert_team(cursor, team2_name)
    cursor.execute('''
    INSERT INTO Matches (match_name, date_played, team1_id, team2_id, team1_score, team2_score, match_winner)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (match_name, date_played, team1_id, team2_id, team1_score, team2_score, match_winner))
    return cursor.lastrowid


def insert_map(cursor, match_id, map_name, team1_score, team2_score, map_winner):
    cursor.execute('''
    INSERT INTO Maps (match_id, map_name, team1_score, team2_score, map_winner)
    VALUES (?, ?, ?, ?, ?)
    ''', (match_id, map_name, team1_score, team2_score, map_winner))
    return cursor.lastrowid


def insert_team_stats(cursor, match_id, team_id, kills, deaths, first_bloods, first_deaths):
    cursor.execute('''
    INSERT INTO Team_Stats (match_id, team_id, kills, deaths, first_bloods, first_deaths)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (match_id, team_id, kills, deaths, first_bloods, first_deaths))


def get_or_insert_player(cursor, player_name, team_id):
    cursor.execute('SELECT player_id FROM Players WHERE player_name = ? AND team_id = ?', (player_name, team_id))
    result = cursor.fetchone()
    if result is None:
        cursor.execute('INSERT INTO Players (player_name, team_id) VALUES (?, ?)', (player_name, team_id))
        return cursor.lastrowid
    else:
        return result[0]


def insert_player_stats(cursor, player_id, map_id, kills, deaths, assists, acs, rating, agent):
    cursor.execute('''
    INSERT INTO Player_Stats (player_id, map_id, kills, deaths, assists, acs, rating, agent)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (player_id, map_id, kills, deaths, assists, acs, rating, agent))


# Function to scrape player stats
def scrape_page(url):
    driver = webdriver.Chrome()
    driver.get(url)

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".vm-stats-gamesnav-item"))
    )

    # Parsing the page source with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    rows = soup.find_all('tr')
    table_data = []
    agents_col = []
    for row in rows:
        cells = row.find_all(['td', 'th'])
        row_data = tuple(cell.get_text().strip() for cell in cells)
        table_data.append(row_data)
        spans = row.find_all('span', class_='mod-agent')
        agent = [img['title'] for img in [span.find('img') for span in spans]]
        agents_col.append(agent[0] if agent else None)

    driver.quit()
    return table_data, agents_col


def parse_player_data(data, agent):
    name_team_split = data[0].split('\n')
    player_name = name_team_split[0].strip()
    team = name_team_split[-1].strip()
    rating = data[2].split('\n')[0].strip()
    acs = data[3].split('\n')[0].strip()
    kills = data[4].split('\n')[0].strip()
    deaths = data[5].split('/\n\n')[-1].split('\n')[0].strip()
    assists = data[6].split('\n')[0].strip()
    plus_minus = data[7].split('\n')[0].strip()
    kast = data[8].split('\n')[0].strip()
    adr = data[9].split('\n')[0].strip()
    hs_percentage = data[10].split('\n')[0].strip()
    fk = data[11].split('\n')[0].strip()
    fd = data[12].split('\n')[0].strip()
    f_plus_minus = data[13].split('\n')[0].strip()

    parsed_data = {
        'player_name': player_name,
        'team': team,
        'agent': agent,
        'rating': float(rating) if rating else 0.0,
        'acs': int(acs) if acs else 0,
        'kills': int(kills) if kills else 0,
        'deaths': int(deaths) if deaths else 0,
        'assists': int(assists) if assists else 0,
        'plus_minus': plus_minus,
        'kast': kast,
        'adr': int(adr) if adr else 0,
        'hs_percentage': hs_percentage,
        'fk': int(fk) if fk else 0,
        'fd': int(fd) if fd else 0,
        'f_plus_minus': f_plus_minus
    }

    return parsed_data


def insert_player_stats_data(cursor, map_id, parsed_data):
    team_id = get_or_insert_team(cursor, parsed_data['team'])
    player_id = get_or_insert_player(cursor, parsed_data['player_name'], team_id)
    insert_player_stats(cursor, player_id, map_id, parsed_data['kills'], parsed_data['deaths'], parsed_data['assists'],
                        parsed_data['acs'], parsed_data['rating'], parsed_data['agent'])


# Function to scrape map names, picks, and scorelines
def scrape_maps_and_scorelines(url):
    driver = webdriver.Chrome()
    driver.get(url)

    maps_and_scorelines = []
    player_stats = []
    agents_col = []

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".vm-stats-gamesnav-item")))
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        map_elements = soup.select('.vm-stats-gamesnav-item:not(.mod-disabled)')

        for map_element in map_elements:
            game_id = map_element['data-game-id']
            map_name = map_element.get_text(strip=True)
            if game_id != "all":  # Skip the 'All Maps' button
                driver.find_element(By.CSS_SELECTOR, f'div[data-game-id="{game_id}"]').click()
                WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, f'.vm-stats-game[data-game-id="{game_id}"] .score')))
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                team_scores = soup.select(f'.vm-stats-game[data-game-id="{game_id}"] .score')
                scoreline = ' - '.join([score.get_text(strip=True) for score in team_scores])
                maps_and_scorelines.append((map_name, scoreline, game_id))

        table_data, agents = scrape_page(url)
        if table_data:
            for line, agent in zip(table_data, agents):
                if line and line[0]:
                    parsed_data = parse_player_data(line, agent)
                    player_stats.append(parsed_data)
                    agents_col.append(agent)

    except TimeoutException:
        print("A timeout occurred while loading the map elements")
    finally:
        driver.quit()

    return maps_and_scorelines, player_stats, agents_col


def main():
    conn = setup_database()
    cursor = conn.cursor()

    url = 'https://www.vlr.gg/295605'
    match_name = "NRG vs FURIA"
    date_played = date(2024, 5, 1)
    team1_name = "NRG"
    team2_name = "FURIA"
    team1_score = 2
    team2_score = 0
    match_winner = "NRG"

    match_id = insert_match(cursor, match_name, date_played, team1_name, team2_name, team1_score, team2_score,
                            match_winner)
    maps, player_stats, agents_col = scrape_maps_and_scorelines(url)

    for idx, (map_name, scoreline, game_id) in enumerate(maps):
        team1_score, team2_score = map(int, scoreline.split(' - '))
        map_winner = team1_name if team1_score > team2_score else team2_name
        map_id = insert_map(cursor, match_id, map_name, team1_score, team2_score, map_winner)

        for i in range(idx * 10, (idx + 1) * 10):
            if i < len(player_stats):
                insert_player_stats_data(cursor, map_id, player_stats[i])

    for idx in range(len(maps) * 10, len(player_stats)):
        insert_player_stats_data(cursor, match_id, player_stats[idx])

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
