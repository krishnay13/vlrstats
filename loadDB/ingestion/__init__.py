"""
Ingestion pipeline for processing matches from URLs.

Provides a unified pipeline that:
1. Loads URLs from files
2. Scrapes match data
3. Applies normalization (aliases)
4. Validates data
5. Inserts into database (skips showmatches)
"""
from .pipeline import ingest_from_urls, IngestionResult
from .url_processor import load_urls_from_file, validate_url, extract_match_id

__all__ = [
    "ingest_from_urls",
    "IngestionResult",
    "load_urls_from_file",
    "validate_url",
    "extract_match_id",
]
