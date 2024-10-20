import json
import requests
from bs4 import BeautifulSoup
from db_init import setup_database


# Function to scrape player stats
def scrape_page(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

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

    return table_data, agents_col


# Function to parse player data
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


# Function to scrape match and map data
def scrape_maps_and_scorelines(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    maps_and_scorelines = []
    player_stats = []
    agents_col = []

    try:
        team1_name = soup.select_one('.match-header-link.mod-1 .match-header-link-name .wf-title-med').get_text(
            strip=True)
        team2_name = soup.select_one('.match-header-link.mod-2 .match-header-link-name .wf-title-med').get_text(
            strip=True)

        scores = soup.select(
            '.match-header-vs-score .js-spoiler .match-header-vs-score-winner, .match-header-vs-score .js-spoiler .match-header-vs-score-loser')
        team1_score = int(scores[0].get_text(strip=True)) if scores else 0
        team2_score = int(scores[1].get_text(strip=True)) if len(scores) > 1 else 0

        map_elements = soup.select('.vm-stats-gamesnav-item:not(.mod-disabled)')
        for map_element in map_elements:
            game_id = map_element['data-game-id']
            map_name = map_element.get_text(strip=True)
            if game_id != "all":  # Skip the 'All Maps' button
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

    except Exception as e:
        print(f"An error occurred: {e}")

    return team1_name, team2_name, team1_score, team2_score, maps_and_scorelines, player_stats, agents_col


# Database insertion functions (adjusted to prevent duplicate teams)
def insert_match(cursor, team1_name, team2_name, team1_score, team2_score, map1_id, map2_id, map3_id, match_stat_ids):
    cursor.execute('''
    INSERT INTO Matches (team1_name, team2_name, team1_score, team2_score, map1_id, map2_id, map3_id,
                         p1_stat_id, p2_stat_id, p3_stat_id, p4_stat_id, p5_stat_id,
                         p6_stat_id, p7_stat_id, p8_stat_id, p9_stat_id, p10_stat_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (team1_name, team2_name, team1_score, team2_score, map1_id, map2_id, map3_id, *match_stat_ids))
    return cursor.lastrowid


def insert_map(cursor, match_id, map_name, team1_name, team2_name, team1_score, team2_score, map_stat_ids):
    cursor.execute('''
    INSERT INTO Maps (match_id, map_name, team1_name, team2_name, team1_score, team2_score,
                      p1_stat_id, p2_stat_id, p3_stat_id, p4_stat_id, p5_stat_id,
                      p6_stat_id, p7_stat_id, p8_stat_id, p9_stat_id, p10_stat_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (match_id, map_name, team1_name, team2_name, team1_score, team2_score, *map_stat_ids))
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


# Processing each match link
def process_match(url, cursor):
    # Scrape match data
    team1_name, team2_name, team1_score, team2_score, maps, player_stats, agents_col = scrape_maps_and_scorelines(url)

    # Extract team names from the first 10 player stats entries (short-form team names)
    team_names = {player_stats[i]['team'] for i in range(10)}
    if len(team_names) != 2:
        print("Error: Could not determine team names from player stats.")
        return
    short_team1_name, short_team2_name = team_names

    # Map full team names to short-form team names
    team_name_mapping = {}
    for name in [team1_name, team2_name]:
        if name.startswith(short_team1_name) or short_team1_name.startswith(name):
            team_name_mapping[name] = short_team1_name
        elif name.startswith(short_team2_name) or short_team2_name.startswith(name):
            team_name_mapping[name] = short_team2_name
        else:
            team_name_mapping[name] = name  # Fallback to full name if no match

    # Update player team names to short form
    for player in player_stats:
        full_team_name = player['team']
        player['team'] = team_name_mapping.get(full_team_name, full_team_name)

    # Insert match with placeholder map IDs and player stat IDs (will update later)
    placeholder_map_ids = [None, None, None]
    placeholder_stat_ids = [None] * 10  # Assuming 10 players in total
    match_id = insert_match(cursor, team1_name, team2_name, team1_score, team2_score,
                            *placeholder_map_ids, placeholder_stat_ids)

    # Get the number of maps
    total_maps = len(maps)
    stats_per_map = 10  # Assuming 10 player stats per map

    # Calculate expected total stats
    expected_stats = stats_per_map * total_maps + stats_per_map  # total_maps maps + match total stats
    if len(player_stats) < expected_stats:
        print("Error: Not enough player stats collected.")
        return

    # Now process the player stats
    partitions = {}
    current_index = 0

    # Map 1 stats
    partitions['map1_stats'] = player_stats[current_index:current_index + stats_per_map]
    current_index += stats_per_map

    # Match total stats
    partitions['match_total_stats'] = player_stats[current_index:current_index + stats_per_map]
    current_index += stats_per_map

    # Remaining map stats
    for i in range(2, total_maps + 1):
        key = f'map{i}_stats'
        partitions[key] = player_stats[current_index:current_index + stats_per_map]
        current_index += stats_per_map

    # Insert match total stats
    match_total_stats = partitions['match_total_stats']
    match_stat_ids = []
    for player in match_total_stats:
        player_id = get_or_insert_player(cursor, player['player_name'], player['team'])
        stat_id = insert_player_stats(cursor, player_id, match_id, None, player)
        match_stat_ids.append(stat_id)

    # Insert maps and collect map_stat_ids
    map_ids = []
    map_stat_ids_list = []
    for i, (map_name, scoreline, game_id) in enumerate(maps):
        team1_map_score, team2_map_score = map(int, scoreline.split(' - '))
        map_player_stats = partitions[f'map{i + 1}_stats']

        map_stat_ids = []
        for player in map_player_stats:
            player_id = get_or_insert_player(cursor, player['player_name'], player['team'])
            stat_id = insert_player_stats(cursor, player_id, match_id, None, player)
            map_stat_ids.append(stat_id)

        # Insert the map with placeholder stat IDs (will update later)
        placeholder_stat_ids = [None] * 10
        map_id = insert_map(cursor, match_id, map_name, team1_name, team2_name, team1_map_score, team2_map_score,
                            placeholder_stat_ids)
        map_ids.append(map_id)
        map_stat_ids_list.append((map_id, map_stat_ids))

    # Now update the player stats with correct map IDs
    for map_id, stat_ids in map_stat_ids_list:
        for stat_id in stat_ids:
            cursor.execute('UPDATE Player_Stats SET map_id = ? WHERE stat_id = ?', (map_id, stat_id))

    # Update the maps with player stat IDs
    for idx, (map_id, stat_ids) in enumerate(map_stat_ids_list):
        cursor.execute('''
        UPDATE Maps SET p1_stat_id = ?, p2_stat_id = ?, p3_stat_id = ?, p4_stat_id = ?, p5_stat_id = ?,
                        p6_stat_id = ?, p7_stat_id = ?, p8_stat_id = ?, p9_stat_id = ?, p10_stat_id = ?
        WHERE map_id = ?
        ''', (*stat_ids, map_id))

    # Update the match with map IDs
    map_ids_to_update = map_ids + [None] * (3 - len(map_ids))  # Ensure there are three map IDs
    cursor.execute('UPDATE Matches SET map1_id = ?, map2_id = ?, map3_id = ? WHERE match_id = ?',
                   (*map_ids_to_update, match_id))

    # Update the match with player stat IDs
    cursor.execute('''
    UPDATE Matches SET p1_stat_id = ?, p2_stat_id = ?, p3_stat_id = ?, p4_stat_id = ?, p5_stat_id = ?,
                       p6_stat_id = ?, p7_stat_id = ?, p8_stat_id = ?, p9_stat_id = ?, p10_stat_id = ?
    WHERE match_id = ?
    ''', (*match_stat_ids, match_id))

    # Insert or update teams using the updated function
    team1_player_ids = []
    team2_player_ids = []
    for i in range(5):
        player = player_stats[i]
        player_id = get_or_insert_player(cursor, player['player_name'], player['team'])
        team1_player_ids.append(player_id)
    for i in range(5, 10):
        player = player_stats[i]
        player_id = get_or_insert_player(cursor, player['player_name'], player['team'])
        team2_player_ids.append(player_id)

    # Use get_or_insert_team to prevent duplicate teams
    get_or_insert_team(cursor, team1_name, team1_player_ids)
    get_or_insert_team(cursor, team2_name, team2_player_ids)


# Main function
def main():
    conn = setup_database()
    cursor = conn.cursor()

    # Read URLs from full_matches.txt
    try:
        with open('full_matches.txt', 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("Error: The file 'full_matches.txt' was not found.")
        return

    # Process each match URL
    for url in urls:
        print(f"Processing match: {url}")
        try:
            process_match(url, cursor)
            # Commit after each successful match processing
            conn.commit()
        except Exception as e:
            print(f"An error occurred while processing {url}: {e}")
            continue  # Move on to the next URL

    # Close the connection after all matches have been processed
    conn.close()


if __name__ == "__main__":
    main()
