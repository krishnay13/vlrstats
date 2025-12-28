from typing import Dict, List, Tuple
from bs4 import BeautifulSoup


def retrieve_urls(
    urls: Dict[str, str],
    tournaments_ids: Dict[str, str],
    tournament_cards: List[BeautifulSoup],
    event_segment: str,
    matches_segment: str,
) -> None:
    """
    Populate `urls` and `tournaments_ids` from a list of tournament <a> cards.

    Args:
        urls: Output mapping of tournament name -> matches URL
        tournaments_ids: Output mapping of tournament name -> event ID (numeric)
        tournament_cards: List of <a> tags that link to tournaments
        event_segment: Expected segment in event URLs (e.g., "/event/")
        matches_segment: Segment to build matches URLs (e.g., "/event/matches/")
    """
    base = "https://www.vlr.gg"
    for a in tournament_cards:
        try:
            name = a.get_text(strip=True)
            href = a.get("href", "")
            if not name or not href:
                continue

            # Normalize to absolute URL
            event_url = href if href.startswith("http") else f"{base}{href}"
            if event_segment not in event_url:
                continue

            # Extract numeric event id: /event/<id>/...
            parts = event_url.split("/")
            event_id = None
            for i, p in enumerate(parts):
                if p == "event" and i + 1 < len(parts):
                    if parts[i + 1].isdigit():
                        event_id = parts[i + 1]
                    break

            if not event_id:
                continue

            tournaments_ids[name] = event_id
            # Build matches URL
            matches_url = f"{base}{matches_segment}{event_id}/"
            urls[name] = matches_url
        except Exception:
            # Skip malformed entries quietly
            continue
