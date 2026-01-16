# Automatic Upcoming Match Ingestion

## Overview

You now have a simple way to ingest matches as soon as they complete without manually finding match IDs!

## Quick Start

The simplest way to use this:

```bash
python ingest_next_completed.py
```

That's it! When a match from your upcoming list completes:
1. Run the command above
2. The system finds the earliest completed upcoming match
3. It automatically ingests the match into your database
4. Elo ratings are recalculated

## How It Works

### Database Query
The script queries for upcoming matches that have:
- ✅ A future `match_ts_utc` (timestamp)
- ✅ Non-NULL scores (`team_a_score` and `team_b_score`)

When a match is completed on vlr.gg, the scores appear in the database automatically. This triggers the ingestion.

### Automatic Elo Recalculation
After a match is ingested, the system automatically:
- Recomputes Elo ratings for 2026 and all-time
- Updates player Elo statistics
- Refreshes frontend rankings

## Two Ways to Use This

### Method 1: Standalone Script (Recommended)
```bash
python ingest_next_completed.py
```

**Advantages:**
- Simple, single command
- No CLI knowledge needed
- Shows match details before ingestion

**Optional flags:**
```bash
python ingest_next_completed.py --no-validate    # Skip data validation (faster)
```

### Method 2: CLI Command
```bash
python -m loadDB.cli ingest-next-completed
```

**Same functionality as the script, uses the CLI framework**

## Example Usage

### Scenario: VCT 2026 Kickoff matches

```bash
# 1. Populate the next 20 upcoming matches (do this daily or as needed)
python -m loadDB.upcoming

# 2. Check the /upcoming-matches page in the frontend
# → See KRÜ vs FURIA, 100T vs LEVIATÁN, etc.

# 3. When KRÜ vs FURIA finishes:
python ingest_next_completed.py

# Output:
# ✓ Found completed upcoming match:
#   Match ID: 596400
#   KRÜ Esports 2-1 FURIA
#   Time: 2026-01-16T22:00:00Z
#
# ⏳ Ingesting match 596400...
# ✓ Done! Match has been ingested and Elo snapshots have been recalculated.

# 4. Repeat for the next match in the list
python ingest_next_completed.py

# Output:
# ✓ Found completed upcoming match:
#   Match ID: 596401
#   100 Thieves 3-0 LEVIATÁN
#   Time: 2026-01-17T02:00:00Z
#
# ⏳ Ingesting match 596401...
# ✓ Done! Match has been ingested and Elo snapshots have been recalculated.
```

## What Happens If There Are No Completed Matches?

```bash
python ingest_next_completed.py

# Output:
# ❌ No completed upcoming matches found.
# Upcoming matches will be ingested once they have scores.
```

This is expected—it just means all upcoming matches are still in progress.

## Behind the Scenes

### Database Query
The script executes this query:
```sql
SELECT match_id, team_a, team_b, team_a_score, team_b_score, match_ts_utc
FROM Matches
WHERE match_ts_utc IS NOT NULL
AND datetime(match_ts_utc, '+5 hours') > datetime('now')
AND team_a_score IS NOT NULL
AND team_b_score IS NOT NULL
ORDER BY match_ts_utc ASC
LIMIT 1
```

This finds the earliest upcoming match that has been completed.

### Ingestion Process
1. Fetches the match page from vlr.gg
2. Extracts match metadata, maps, and player stats
3. Validates the data
4. Stores in database
5. Automatically recalculates Elo snapshots

### Elo Recalculation
The system uses `compute_elo_snapshots()` which:
- Preserves historical 2024/2025 snapshots
- Recomputes 2026 (active season)
- Recomputes all-time rankings
- Updates player Elo statistics

## Troubleshooting

### Issue: Script says "No completed upcoming matches found"
**Cause**: None of your upcoming matches have completed yet.
**Solution**: Wait for matches to complete, or check vlr.gg to see if any have finished.

### Issue: Ingestion fails with validation error
**Solution**: Try with `--no-validate` flag to skip data validation:
```bash
python ingest_next_completed.py --no-validate
```

### Issue: Elo ratings seem unchanged after ingestion
**Cause**: This is normal if the ingested match doesn't change team rankings significantly.
**Verification**: Check the `/api/elo` endpoint or rankings page to confirm the new match was recorded.

## Advanced: Manual Ingestion

If you ever want to ingest a specific match by ID:

```bash
# Single match
python -m loadDB.cli ingest 596400

# Multiple matches
python -m loadDB.cli ingest 596400 596401 596402
```

The automatic Elo recalculation happens after ingestion just like with `ingest_next_completed.py`.
