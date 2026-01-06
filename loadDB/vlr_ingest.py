import re
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from .db_utils import get_conn, ensure_matches_columns, upsert_match, upsert_maps, upsert_player_stats


def match_id_from_url(url: str) -> int | None:
    m = re.search(r"/([0-9]+)/", url)
    return int(m.group(1)) if m else None


async def fetch_html(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url, timeout=20) as resp:
        resp.raise_for_status()
        return await resp.text()


def _parse_dt_utc(soup: BeautifulSoup) -> str | None:
    # Try common patterns on vlr.gg pages
    t = soup.select_one('.match-header-date .moment-tz-convert')
    if t and t.has_attr('data-utc-ts'):
        try:
            ts = int(t['data-utc-ts'])
            return datetime.utcfromtimestamp(ts).isoformat() + 'Z'
        except Exception:
            pass
    if t and t.get_text(strip=True):
        raw = t.get_text(' ', strip=True)
        for fmt in ("%b %d, %Y - %H:%M %Z", "%b %d, %Y - %H:%M"):
            try:
                dt = datetime.strptime(raw, fmt)
                return dt.isoformat() + 'Z'
            except Exception:
                continue
    return None


def _clean_map_name(text: str) -> str:
    KNOWN = ['Ascent', 'Bind', 'Breeze', 'Fracture', 'Haven', 'Icebox', 'Lotus', 'Pearl', 'Split', 'Sunset', 'Abyss', 'Corrode']
    for km in KNOWN:
        if re.search(rf"\b{re.escape(km)}\b", text, re.IGNORECASE):
            return km
    return re.sub(r"\s+", " ", text).strip('- ').strip()


async def scrape_match(match_id_or_url: str | int) -> tuple[tuple, list[tuple], list[tuple]]:
    url = f"https://www.vlr.gg/{match_id_or_url}" if isinstance(match_id_or_url, int) else str(match_id_or_url)
    mid = match_id_from_url(url) if not isinstance(match_id_or_url, int) else match_id_or_url
    async with aiohttp.ClientSession() as session:
        html = await fetch_html(session, url)
    soup = BeautifulSoup(html, 'html.parser')

    teams = soup.select('.match-header-link-name .wf-title-med')
    team_a = teams[0].get_text(strip=True) if len(teams) > 0 else 'Unknown'
    team_b = teams[1].get_text(strip=True) if len(teams) > 1 else 'Unknown'

    score_spans = soup.select('.match-header-vs-score .js-spoiler span, .match-header-vs-score span')
    a_score = b_score = 0
    if len(score_spans) >= 2:
        try:
            a_score = int(score_spans[0].get_text(strip=True))
            b_score = int(score_spans[1].get_text(strip=True))
        except Exception:
            a_score = b_score = 0

    match_name_elem = soup.select_one('.match-header-event')
    match_name = match_name_elem.get_text(' ', strip=True) if match_name_elem else url.split('/')[-1]
    stage = ''
    match_type = ''
    tournament = ''
    parts = [p.strip() for p in match_name.split(':')]
    if parts:
        tournament = parts[0]
    if len(parts) >= 2:
        match_type = parts[-1]
        stage_token = parts[-2]
        m = re.search(r'(Main Event|Group Stage|Swiss Stage|Playoffs|Knockout Stage|Stage\s*[12]|Kickoff)', stage_token, re.IGNORECASE)
        stage = m.group(1) if m else stage_token

    dt_utc = _parse_dt_utc(soup)

    maps_info: list[tuple] = []
    players_info: list[tuple] = []
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
        map_name = _clean_map_name(map_name or 'Unknown')

        a_map_score = b_map_score = None
        if header:
            header_text = header.get_text(' ', strip=True)
            m = re.search(r'(\d{1,2})\s*-\s*(\d{1,2})', header_text)
            if m:
                try:
                    a_map_score = int(m.group(1)); b_map_score = int(m.group(2))
                except Exception:
                    a_map_score = b_map_score = None

        if a_map_score is not None and b_map_score is not None:
            maps_info.append((mid, game_id, map_name, a_map_score, b_map_score))

        if a_map_score is None or b_map_score is None:
            continue
        for row in game_div.select('table.wf-table-inset tbody tr'):
            cells = row.find_all('td')
            if len(cells) < 7:
                continue
            player_cell = cells[0]
            player = (player_cell.find('div', class_='text-of') or {}).get_text(strip=True) if player_cell else None
            team = (player_cell.find('div', class_='ge-text-light') or {}).get_text(strip=True) if player_cell else None
            img = row.find('img')
            agent = (img.get('title') or img.get('alt')) if img else None

            def first_num(text, default=0.0, as_int=False):
                text = (text or '').strip()
                parts = text.split()
                for part in parts:
                    cleaned = ''.join(c for c in part if c.isdigit() or c in '.-')
                    if cleaned and cleaned not in '.-':
                        try:
                            val = float(cleaned)
                            return int(val) if as_int else val
                        except Exception:
                            continue
                return default

            rating = first_num(cells[2].get_text(), 0.0)
            acs = first_num(cells[3].get_text(), 0, as_int=True)
            kills = first_num(cells[4].get_text(), 0, as_int=True)
            deaths = first_num(cells[5].get_text(), 0, as_int=True)
            assists = first_num(cells[6].get_text(), 0, as_int=True)
            if player:
                players_info.append((mid, game_id, player, team or 'Unknown', agent or 'Unknown', rating, acs, kills, deaths, assists))

    if any(tas is not None and tbs is not None for _, _, _, tas, tbs in maps_info):
        a_w = sum(1 for _, _, _, tas, tbs in maps_info if tas is not None and tbs is not None and tas > tbs)
        b_w = sum(1 for _, _, _, tas, tbs in maps_info if tas is not None and tbs is not None and tbs > tas)
        if (a_score + b_score) < 2 or (a_score + b_score) != (a_w + b_w):
            a_score, b_score = a_w, b_w

    match_row = (
        mid, tournament, stage, match_type, match_name,
        team_a, team_b, a_score, b_score, f"{team_a} {a_score}-{b_score} {team_b}", dt_utc
    )
    return match_row, maps_info, players_info


async def ingest_matches(ids_or_urls: list[str | int]) -> None:
    conn = get_conn()
    ensure_matches_columns(conn)
    for item in ids_or_urls:
        match_row, maps_info, players_info = await scrape_match(item)
        upsert_match(conn, match_row)
        m_lookup = upsert_maps(conn, maps_info)
        upsert_player_stats(conn, players_info, m_lookup)
        conn.commit()
    conn.close()


def ingest(ids_or_urls: list[str | int]) -> None:
    asyncio.run(ingest_matches(ids_or_urls))
