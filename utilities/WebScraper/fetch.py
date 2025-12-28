import asyncio
from typing import Dict, List, Any, Tuple
from bs4 import BeautifulSoup


async def _fetch(session, url: str, semaphore: asyncio.Semaphore) -> Tuple[str, str]:
    async with semaphore:
        async with session.get(url, timeout=20) as resp:
            resp.raise_for_status()
            text = await resp.text()
            return url, text


def _parse_match(html: str) -> Dict[str, Any]:
    """Parse a single VLR.gg match page into minimal fields.
    Returns keys: match_name, team_a, team_b, team_a_score, team_b_score, players
    """
    soup = BeautifulSoup(html, "html.parser")

    # Teams
    teams = soup.select('.match-header-link-name .wf-title-med')
    team_a = teams[0].get_text(strip=True) if len(teams) > 0 else "Unknown"
    team_b = teams[1].get_text(strip=True) if len(teams) > 1 else "Unknown"
    match_name = f"{team_a} vs {team_b}"

    # Score
    score_spans = soup.select('.match-header-vs-score .js-spoiler span')
    def _to_int(t: str) -> int:
        try:
            return int(t.strip())
        except Exception:
            return 0
    team_a_score = _to_int(score_spans[0].get_text()) if len(score_spans) > 0 else 0
    team_b_score = _to_int(score_spans[1].get_text()) if len(score_spans) > 1 else 0

    # Player overview from All Maps table
    all_div = soup.find('div', {'data-game-id': 'all'}) or soup.find('div', class_='vm-stats-game')
    rows = (all_div.select('table.wf-table-inset tbody tr') if all_div
            else soup.select('table.wf-table-inset tbody tr'))

    players = []
    for row in rows[:10]:
        tds = row.find_all('td')
        if len(tds) < 7:
            continue
        pcell = tds[0]
        name_el = pcell.find('div', class_='text-of')
        team_el = pcell.find('div', class_='ge-text-light')
        agent_el = pcell.find('img', class_='mod-sm')
        name = name_el.get_text(strip=True) if name_el else 'Unknown'
        team = team_el.get_text(strip=True) if team_el else 'Unknown'
        agent = agent_el.get('title', 'Unknown') if agent_el else 'Unknown'

        def _num(text: str, as_int: bool = False):
            text = (text or '').strip()
            for part in text.replace('\n', ' ').split():
                clean = ''.join(c for c in part if c.isdigit() or c in '.-')
                if clean and clean not in '.-':
                    try:
                        val = float(clean)
                        return int(val) if as_int else val
                    except Exception:
                        pass
            return 0 if as_int else 0.0

        rating = _num(tds[2].get_text() if len(tds) > 2 else '')
        acs = _num(tds[3].get_text() if len(tds) > 3 else '', as_int=True)
        kills = _num(tds[4].get_text() if len(tds) > 4 else '', as_int=True)
        deaths = _num(tds[5].get_text() if len(tds) > 5 else '', as_int=True)
        assists = _num(tds[6].get_text() if len(tds) > 6 else '', as_int=True)

        players.append({
            'player_name': name,
            'team': team,
            'agent': agent,
            'rating': rating,
            'acs': acs,
            'kills': kills,
            'deaths': deaths,
            'assists': assists,
        })

    return {
        'match_name': match_name,
        'team_a': team_a,
        'team_b': team_b,
        'team_a_score': team_a_score,
        'team_b_score': team_b_score,
        'players': players,
    }


async def scraping_matches_data(
    tournament_name: str,
    cards: List[Any],
    tournaments_ids: Dict[str, str],
    stages_ids: Dict[str, Dict[str, str]],
    matches_semaphore: asyncio.Semaphore,
    session,
) -> List[Dict[str, List[Any]]]:
    """
    Async scrape matches for a tournament, returning buckets matching the external script.
    Only populates minimal buckets: scores and overview; others empty.
    """
    base = "https://www.vlr.gg"
    match_urls: List[str] = []
    for a in cards:
        href = a.get('href') if hasattr(a, 'get') else None
        if not href:
            continue
        # Accept links that look like /<numeric>/...
        parts = href.split('/')
        if len(parts) >= 3 and parts[1].isdigit():
            url = f"{base}{href}" if href.startswith('/') else href
            match_urls.append(url)

    # Fetch pages concurrently
    tasks = [_fetch(session, url, matches_semaphore) for url in match_urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    scores: List[List[Any]] = []
    overview: List[List[Any]] = []

    for item in results:
        if isinstance(item, Exception):
            continue
        url, html = item
        parsed = _parse_match(html)

        # Minimal placeholders for Stage/Match Type
        stage = "Unknown"
        match_type = "Unknown"
        match_name = parsed['match_name']

        # Scores
        scores.append([
            tournament_name,
            stage,
            match_type,
            match_name,
            parsed['team_a'],
            parsed['team_b'],
            parsed['team_a_score'],
            parsed['team_b_score'],
            f"{parsed['team_a_score']}-{parsed['team_b_score']}",
        ])

        # Overview rows
        for p in parsed['players']:
            overview.append([
                tournament_name,
                stage,
                match_type,
                match_name,
                'All',  # Map scope
                p['player_name'],
                p['team'],
                p['agent'],
                p['rating'],
                p['acs'],
                p['kills'],
                p['deaths'],
                p['assists'],
                p['kills'] - p['deaths'],  # KD
                None,  # KAST - not parsed
                None,  # ADR - not parsed
                None,  # HS%
                None,  # First Kills
                None,  # First Deaths
                None,  # FKD
                'All',  # Side (placeholder)
            ])

    return [{
        'scores': scores,
        'maps_played': [],
        'maps_scores': [],
        'draft_phase': [],
        'win_loss_methods_count': [],
        'win_loss_methods_round_number': [],
        'overview': overview,
        'kills': [],
        'kills_stats': [],
        'rounds_kills': [],
        'eco_stats': [],
        'eco_rounds': [],
        'team_mapping': {},
        'teams_ids': {},
        'players_ids': {},
        'tournaments_stages_matches_games_ids': [],
    }]


# Placeholders for player stats logic to satisfy imports
async def generate_urls_combination(*args, **kwargs):
    return None


async def scraping_players_stats(*args, **kwargs):
    return []
