# Legacy Loaders and Scrapers (Deprecated)

These scripts have been deprecated in favor of the new modular CLI and ingest pipeline.

Use instead:
- Ingest matches: `python -m loadDB.cli ingest <match_id_or_url> ...`
- Compute Elo: `python -m loadDB.cli elo compute --save`
- Show rankings/history: `python -m loadDB.cli show ...`

Deprecated files now emit a clear message and exit:
- `scrape.py` (bulk/event scraper)
- `async_scores_overview_scraper.py`
- `db_init.py` / `init_db.py`
- `team_cleanup.py` / `map_cleanup.py`

If you need any functionality restored, consider adding it as a focused subcommand to `loadDB/cli.py`.
