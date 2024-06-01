import requests
from bs4 import BeautifulSoup

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


def scrape_maps_and_scorelines(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    maps_and_scorelines = []
    player_stats = []
    agents_col = []

    team1_name = soup.select_one('.wf-title-med:nth-of-type(1)').get_text(strip=True)
    team2_name = soup.select_one('.wf-title-med:nth-of-type(2)').get_text(strip=True)
    team1_score = int(soup.select('.js-spoiler .match-header-vs-score')[0].get_text(strip=True))
    team2_score = int(soup.select('.js-spoiler .match-header-vs-score')[1].get_text(strip=True))

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

    return team1_name, team2_name, team1_score, team2_score, maps_and_scorelines, player_stats, agents_col


def main():
    url = 'https://www.vlr.gg/314634'

    team1_name, team2_name, team1_score, team2_score, maps, player_stats, agents_col = scrape_maps_and_scorelines(url)

    print(f"Team 1: {team1_name} (Score: {team1_score})")
    print(f"Team 2: {team2_name} (Score: {team2_score})")

    print("Maps and Scorelines:")
    for map_name, scoreline, game_id in maps:
        team1_map_score, team2_map_score = scoreline.split(' - ')
        print(f"{map_name} {team1_name} {team1_map_score} - {team2_name} {team2_map_score}")

    print("Player Stats:")
    for player in player_stats:
        print(player)


if __name__ == "__main__":
    main()
