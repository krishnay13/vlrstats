import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import sqlite3
import os

base_dir = os.path.dirname(__file__)
DB_PATH = os.path.abspath(os.path.join(base_dir, '..', 'valorant_esports.db'))

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

async def parse_match(session: aiohttp.ClientSession, event_name: str, match_url: str):
    html = await fetch(session, match_url)
    soup = BeautifulSoup(html, 'html.parser')
    m_id = re.search(r"/(\d+)/", match_url)
    match_id = int(m_id.group(1)) if m_id else None

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

    match_name_elem = soup.select_one('.match-header-event')
    match_name = match_name_elem.get_text(' ', strip=True) if match_name_elem else match_url.split('/')[-1]
    stage = ''
    match_type = ''
    parts = [p.strip() for p in match_name.split(':')]
    if len(parts) >= 2:
        match_type = parts[-1]
        stage_token = parts[-2]
        stage_match = re.search(r'(Main Event|Group Stage|Swiss Stage|Playoffs|Knockout Stage|Stage\s*[12]|Kickoff)', stage_token, re.IGNORECASE)
        stage = stage_match.group(1) if stage_match else stage_token

    maps_info = []
    players_info = []
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
        map_name_clean = re.sub(r"(?i)pick|ban", "", map_name)
        map_name_clean = re.sub(r"\d{1,2}:(?:\d{2}(?::\d{2})?)?", "", map_name_clean)
        map_name_clean = re.sub(r"[0-9:]+", "", map_name_clean)
        map_name_clean = map_name_clean.strip().strip('-')
        KNOWN_MAPS = ['Ascent','Bind','Breeze','Fracture','Haven','Icebox','Lotus','Pearl','Split','Sunset','Abyss','Corrode']
        for km in KNOWN_MAPS:
            if re.search(rf"\b{re.escape(km)}\b", map_name, re.IGNORECASE):
                map_name_clean = km
                break

        a_map_score = None
        b_map_score = None
        if header:
            header_text = header.get_text(' ', strip=True)
            m = re.search(r'(\d{1,2})\s*-\s*(\d{1,2})', header_text)
            if m:
                try:
                    a_map_score = int(m.group(1))
                    b_map_score = int(m.group(2))
                except:
                    a_map_score = b_map_score = None
            if a_map_score is None or b_map_score is None:
                score_elems = header.find_all(class_=re.compile(r'score|vs-score|header-score'))
                nums = []
                for se in score_elems:
                    for token in re.findall(r'\b\d{1,2}\b', se.get_text(' ', strip=True)):
                        try:
                            nums.append(int(token))
                        except:
                            pass
                if len(nums) >= 2:
                    a_map_score, b_map_score = nums[0], nums[1]
            if a_map_score is None or b_map_score is None:
                nums = []
                for token in re.findall(r'\b\d{1,2}\b', header_text):
                    try:
                        nums.append(int(token))
                    except:
                        pass
                if len(nums) >= 2:
                    a_map_score, b_map_score = nums[0], nums[1]

        # Store None when scores are missing to avoid misleading 0s
        # Only record played maps (both scores present)
        if a_map_score is not None and b_map_score is not None:
            maps_info.append((match_id, game_id, map_name_clean, a_map_score, b_map_score))

        player_rows = game_div.select('table.wf-table-inset tbody tr')
        # Only record player stats for played maps
        if a_map_score is None or b_map_score is None:
            continue
        for row in player_rows:
            cells = row.find_all('td')
            if len(cells) < 7:
                continue
            player_cell = cells[0]
            player_name_elem = player_cell.find('div', class_='text-of')
            team_elem = player_cell.find('div', class_='ge-text-light')
            player = player_name_elem.get_text(strip=True) if player_name_elem else 'Unknown'
            team = team_elem.get_text(strip=True) if team_elem else 'Unknown'
            img = row.find('img')
            agent = (img.get('title') or img.get('alt')) if img else 'Unknown'

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

            players_info.append((match_id, game_id, player, team, agent, rating, acs, kills, deaths, assists))

    # Fallback/recovery: derive series score from per-map results when header is missing or implausible (e.g., 1-0)
    if any(tas is not None and tbs is not None for _, _, _, tas, tbs in maps_info):
        a_wins = sum(1 for _, _, _, tas, tbs in maps_info if tas is not None and tbs is not None and tas > tbs)
        b_wins = sum(1 for _, _, _, tas, tbs in maps_info if tas is not None and tbs is not None and tbs > tas)
        wins_sum = a_wins + b_wins
        # If header says 0-0 or implausible sum, or header sum doesn't match map winners, trust computed wins
        if (a_score + b_score) < 2 or (a_score + b_score) != wins_sum:
            a_score, b_score = a_wins, b_wins

    match_row = (match_id, event_name, stage, match_type, match_name, team_a, team_b, a_score, b_score, f"{team_a} {a_score}-{b_score} {team_b}")

    return match_row, maps_info, players_info

async def main():
    async with aiohttp.ClientSession() as session:
        all_matches = []
        all_maps = []
        all_player_stats = []
        sem = asyncio.Semaphore(10)
        for ev_url in VCT_2025_EVENTS:
            event_name = ev_url.split('/')[-1].replace('-', ' ').title()
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

            async def bounded_parse(mu):
                async with sem:
                    return await parse_match(session, event_name, mu)
            tasks = [bounded_parse(mu) for mu in match_urls]
            try:
                results = await asyncio.gather(*tasks)
                for match_row, maps_info, players_info in results:
                    all_matches.append(match_row)
                    all_maps.extend(maps_info)
                    all_player_stats.extend(players_info)
            except Exception as e:
                print(f"[ERR] parsing batch for {event_name}: {e}")

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Upsert matches (update scores if already present)
        cur.executemany('''
            INSERT INTO Matches (match_id, tournament, stage, match_type, match_name, team_a, team_b, team_a_score, team_b_score, match_result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(match_id) DO UPDATE SET
                tournament=excluded.tournament,
                stage=excluded.stage,
                match_type=excluded.match_type,
                match_name=excluded.match_name,
                team_a=excluded.team_a,
                team_b=excluded.team_b,
                team_a_score=excluded.team_a_score,
                team_b_score=excluded.team_b_score,
                match_result=excluded.match_result
        ''', all_matches)

        # Upsert maps and build (match_id, game_id) -> map_id mapping
        map_id_lookup = {}
        for match_id, game_id, map_name, ta_score, tb_score in all_maps:
            cur.execute('''
                INSERT INTO Maps (match_id, game_id, map, team_a_score, team_b_score)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(match_id, game_id) DO UPDATE SET
                    map=excluded.map,
                    team_a_score=excluded.team_a_score,
                    team_b_score=excluded.team_b_score
            ''', (match_id, game_id, map_name, ta_score, tb_score))
            # Resolve the map_id reliably after upsert
            cur.execute('SELECT id FROM Maps WHERE match_id = ? AND game_id = ?', (match_id, game_id))
            row = cur.fetchone()
            if row:
                map_id_lookup[(match_id, game_id)] = row[0]

        # Upsert player stats using resolved map_id
        for match_id, game_id, player, team, agent, rating, acs, kills, deaths, assists in all_player_stats:
            map_id = map_id_lookup.get((match_id, game_id))
            if map_id is None:
                cur.execute('SELECT id FROM Maps WHERE match_id = ? AND game_id = ?', (match_id, game_id))
                row = cur.fetchone()
                map_id = row[0] if row else None
            cur.execute('''
                INSERT INTO Player_Stats (match_id, map_id, game_id, player, team, agent, rating, acs, kills, deaths, assists)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(match_id, map_id, player) DO UPDATE SET
                    team=excluded.team,
                    agent=excluded.agent,
                    rating=excluded.rating,
                    acs=excluded.acs,
                    kills=excluded.kills,
                    deaths=excluded.deaths,
                    assists=excluded.assists
            ''', (match_id, map_id, game_id, player, team, agent, rating, acs, kills, deaths, assists))

        conn.commit()
        conn.close()
        print(f"[OK] Inserted/Updated {len(all_matches)} matches, {len(all_maps)} maps, and {len(all_player_stats)} player stat rows into the database.")

if __name__ == '__main__':
    asyncio.run(main())
