from bs4 import BeautifulSoup
import requests


def scrape_page(url):
    response = requests.get(url)
    if response.status_code == 200:
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
            agents_col.append(agent[0] if len(agent) != 0 else " ")
        return table_data
    else:
        print(f"Failed to retrieve the page: {url}")
        return None


# Given raw data
raw_data = (
'zeek \n\t\t\t\t\t\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\t\t\t\t\n\n\t\t\t\t\t\t\t\t\t\t\t\t\t\n\t\t\t\t\t\t\t\t\t\t\t\t\tGN',
'', '1.37\n1.42\n1.27', '304\n338\n238', '17\n13\n4', '/\n\n15\n10\n5\n\n/', '6\n2\n4', '+2\n+3\n-1', '78%\n83%\n67%',
'209\n226\n176', '21%\n26%\n13%', '4\n4\n0', '2\n2\n0', '+2\n+2\n0')


def parse_player_data(data):
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
        'Player name': player_name,
        'Team': team,
        'Rating': rating,
        'ACS': acs,
        'Kills': kills,
        'Deaths': deaths,
        'Assists': assists,
        '+/-': plus_minus,
        'KAST': kast,
        'ADR': adr,
        'HS%': hs_percentage,
        'FK': fk,
        'FD': fd,
        'F+/-': f_plus_minus
    }

    return parsed_data


parsed_stats = parse_player_data(raw_data)

links = [f'https://www.vlr.gg/{i}' for i in range(295605, 295620)]

for link in links:
    page_data = scrape_page(link)
    if page_data:
        print(f"Data from {link}:")
        map_counter = 0
        for line in page_data:
            stats = parse_player_data(line)
            print(parse_player_data(line))

        #break
    else:
        print(f"No data could be scraped from {link}.")
