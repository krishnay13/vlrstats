# Ingestion Pipeline

Simple URL-based ingestion system for VLR.gg matches.

## Usage

### Basic Usage

Create a text file with URLs (one per line):

```
https://www.vlr.gg/427991/match-name
https://www.vlr.gg/428000/another-match
```

Then run:
```bash
python -m loadDB.cli ingest-from-file matches.txt
```

### Per-Line Match Type Specification

You can specify match type per URL using comments. The match type indicates the tournament tier:

- **VCT** = Tier 1 Valorant (Champions Tour)
- **VCL** = Tier 2 Valorant (Challengers)
- **OFFSEASON** = Offseason events (may mix tier 1 and tier 2 teams)

```
https://www.vlr.gg/427991/match-name # VCT
https://www.vlr.gg/428000/another-match # VCL
https://www.vlr.gg/428100/third-match # OFFSEASON
https://www.vlr.gg/428200/fourth-match  # Auto-detect from tournament name
```

**Important:** Showmatches are automatically filtered out regardless of specified match type. Even if a VCT tournament contains showmatches, they will be skipped.

### Global Match Type Override

Override match type for all URLs:
```bash
python -m loadDB.cli ingest-from-file matches.txt --match-type VCT
```

### Showmatch Handling

**Showmatches are automatically skipped** during ingestion. They will not be inserted into the database.

To remove existing showmatches from the database:
```bash
python -m loadDB.cli remove-showmatches
```

Preview what would be deleted:
```bash
python -m loadDB.cli remove-showmatches --dry-run
```

## File Format

- One URL per line
- Empty lines are ignored
- Lines starting with `#` are treated as comments
- Per-line match type: `URL # VCT` or `URL #VCT` (space optional)
- Supported match types: `VCT`, `VCL`, `OFFSEASON`

## Features

- Automatic normalization (teams, maps, tournaments, match types)
- Data validation
- Showmatch filtering
- Per-URL or global match type specification
- Error handling and reporting
