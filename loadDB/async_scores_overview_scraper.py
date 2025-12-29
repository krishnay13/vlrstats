import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import sqlite3

DB_PATH = '../valorant_esports.db'

# Explicit VCT 2025 events (matches pages) for broader coverage, excluding showmatches later.
VCT_2025_EVENTS = [
    "https://www.vlr.gg/event/2275/vct-2025-china-kickoff",
    "https://www.vlr.gg/event/2274/vct-2025-americas-kickoff",
    "https://www.vlr.gg/event/2277/vct-2025-pacific-kickoff",
    "https://www.vlr.gg/event/2276/vct-2025-emea-kickoff",
    "https://www.vlr.gg/event/2281/valorant-masters-bangkok-2025",
    "https://www.vlr.gg/event/2347/vct-2025-americas-stage-1",
    "https://www.vlr.gg/event/2359/vct-2025-china-stage-1",
    "https://www.vlr.gg/event/2379/vct-2025-pacific-stage-1",
    "https://www.vlr.gg/event/2380/vct-2025-emea-stage-1",
    "https://www.vlr.gg/event/2282/valorant-masters-toronto-2025",
    "https://www.vlr.gg/event/2499/vct-2025-china-stage-2",
    "https://www.vlr.gg/event/2500/vct-2025-pacific-stage-2",
    "https://www.vlr.gg/event/2498/vct-2025-emea-stage-2",
    "https://www.vlr.gg/event/2501/vct-2025-americas-stage-2",
    "https://www.vlr.gg/event/2283/valorant-champions-2025",
]

async def fetch(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url, timeout=20) as resp:
        resp.raise_for_status()
        return await resp.text()

# No root discovery needed; we use a fixed event list.

async def parse_match(session: aiohttp.ClientSession, event_name: str, match_url: str) -> tuple[list,list]:
    html = await fetch(session, match_url)
    soup = BeautifulSoup(html, 'html.parser')
    # Teams and header score
    teams = soup.select('.match-header-link-name .wf-title-med')
    team_a = teams[0].get_text(strip=True) if len(teams) > 0 else 'Unknown'
    team_b = teams[1].get_text(strip=True) if len(teams) > 1 else 'Unknown'
    score_spans = soup.select('.match-header-vs-score .js-spoiler span, .match-header-vs-score span')
    a_score = b_score = 0
    if len(score_spans) >= 2:
        try:
            a_score = int(score_spans[0].get_text(strip=True))
            b_score = int(score_spans[1].get_text(strip=True))
        except:
            pass
    # Match name (from header title)
    match_name_elem = soup.select_one('.match-header-event')
    match_name = match_name_elem.get_text(' ', strip=True) if match_name_elem else match_url.split('/')[-1]
    # Scores row
    scores_row = [event_name, '', '', match_name, team_a, team_b, a_score, b_score, f"{team_a} {a_score}-{b_score} {team_b}"]
    # Overview rows per map
    overview_rows = []
    for game_div in soup.select('div.vm-stats-game'):
        game_id = game_div.get('data-game-id')
        if not game_id or game_id == 'all':
            continue
        header = game_div.find('div', class_='vm-stats-game-header')
        map_name = None
        if header:
            name_elem = header.find(class_='map')
            if name_elem:
                map_name = name_elem.get_text(strip=True)
        if not map_name:
            nav_item = soup.find('a', class_='vm-stats-gamesnav-item', attrs={'data-game-id': game_id})
            map_name = nav_item.get_text(strip=True) if nav_item else 'Unknown'
        # Player rows
        player_rows = game_div.select('table.wf-table-inset tbody tr')
        for row in player_rows:
            cells = row.find_all('td')
            if len(cells) < 7:
                continue
            player_cell = cells[0]
            player_name_elem = player_cell.find('div', class_='text-of')
            team_elem = player_cell.find('div', class_='ge-text-light')
            player = player_name_elem.get_text(strip=True) if player_name_elem else 'Unknown'
            team = team_elem.get_text(strip=True) if team_elem else 'Unknown'
            # Agent
            img = row.find('img')
            agent = (img.get('title') or img.get('alt')) if img else 'Unknown'
            # Extract numeric stats
            def first_num(text, default=0.0, as_int=False):
                text = (text or '').strip()
                parts = text.split()
                for part in parts:
                    cleaned = ''.join(c for c in part if c.isdigit() or c in '.-')
                    if cleaned and cleaned not in '.-':
                        try:
                            val = float(cleaned)
                            return int(val) if as_int else val
                        except:
                            continue
                return default
            rating = first_num(cells[2].get_text(), 0.0)
            acs = first_num(cells[3].get_text(), 0, as_int=True)
            kills = first_num(cells[4].get_text(), 0, as_int=True)
            deaths = first_num(cells[5].get_text(), 0, as_int=True)
            assists = first_num(cells[6].get_text(), 0, as_int=True)
            # Optional fields
            kd = ''
            kast = ''
            adr = 0
            hs = ''
            fk = 0
            fd = 0
            fkd = ''
            side = ''
            overview_rows.append([event_name, '', '', match_name, map_name, player, team, agent, rating, acs, kills, deaths, assists, kd, kast, adr, hs, fk, fd, fkd, side])
    return [scores_row], overview_rows

async def main():
    # Use explicit event list for full coverage
    async with aiohttp.ClientSession() as session:
        all_scores = []
        all_overview = []
        sem = asyncio.Semaphore(10)
        for ev_url in VCT_2025_EVENTS:
            # Derive event name from URL for labeling
            event_name = ev_url.split('/')[-1].replace('-', ' ').title()
            # Build matches page URL
            event_id = ev_url.split('/')[4]
            matches_url = f"https://www.vlr.gg/event/matches/{event_id}/"
            try:
                html = await fetch(session, matches_url)
            except Exception:
                html = await fetch(session, ev_url)
            soup = BeautifulSoup(html, 'html.parser')
            match_urls = []
            for a in soup.find_all('a', href=re.compile(r'^/\d+/[^/]+')):
                href = a.get('href', '')
                parts = href.split('/')
                if len(parts) >= 3 and parts[1].isdigit():
                    t = a.get_text(' ', strip=True).lower()
                    if 'showmatch' in href.lower() or 'showmatch' in t:
                        continue
                    match_urls.append(f"https://www.vlr.gg{href}")
            match_urls = list(dict.fromkeys(match_urls))
            # Parse matches with bounded concurrency
            async def bounded_parse(mu):
                async with sem:
                    return await parse_match(session, event_name, mu)
            tasks = [bounded_parse(mu) for mu in match_urls]
            try:
                results = await asyncio.gather(*tasks)
                for scores, overview in results:
                    all_scores.extend(scores)
                    all_overview.extend(overview)
            except Exception as e:
                print(f"[ERR] parsing batch for {event_name}: {e}")
        # Insert into DB
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.executemany('''
            INSERT INTO Scores (tournament, stage, match_type, match_name, team_a, team_b, team_a_score, team_b_score, match_result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', all_scores)
        cur.executemany('''
            INSERT INTO Overview (tournament, stage, match_type, match_name, map, player, team, agents, rating, average_combat_score, kills, deaths, assists, kd, kast, adr, headshot_pct, first_kills, first_deaths, fkd, side)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', all_overview)
        conn.commit()
        conn.close()
        print(f"[OK] Inserted {len(all_scores)} scores and {len(all_overview)} overview rows into the database.")

if __name__ == '__main__':
    asyncio.run(main())
