"""
Scraper modules for extracting data from VLR.gg.

Each scraper module handles extraction of specific data types:
- base: Common utilities (HTTP fetching, URL parsing)
- match: Match metadata extraction
- maps: Map data extraction
- players: Player statistics extraction
"""
from .base import fetch_html, match_id_from_url

__all__ = [
    "fetch_html",
    "match_id_from_url",
]
