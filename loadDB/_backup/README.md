# Backup Folder

This folder contains old/unused code that has been replaced by the new modular structure.

## Files

- **aliases.json** - Old team aliases file (replaced by `aliases/teams.json`)
- **vlr_ingest_old.py** - Backup of old monolithic ingestion file (1300+ lines)

## Migration Notes

The old `vlr_ingest.py` has been replaced with a thin compatibility wrapper (~80 lines) that uses the new modular code:
- `scrapers/` - Modular scrapers (base, match, maps, players)
- `ingestion/` - Ingestion pipeline
- `normalizers/` - Entity normalization with aliases
- `aliases/` - Unified alias system

All existing imports from `vlr_ingest` continue to work through the compatibility wrapper.

**Note:** If you need the original 1300+ line `vlr_ingest.py` file, it can be restored from git history (commit before modularization).
