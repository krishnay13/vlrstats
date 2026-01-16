# Upcoming Matches Implementation Summary

## Overview
Implemented end-to-end upcoming matches functionality for the VCT homepage. The system now:
- Scrapes the next 20 matches from the 4 VCT 2026 Kickoff events
- Stores match IDs and projected start times in the database
- Displays upcoming matches on the homepage with TBD opponent handling
- Supports future automation for post-match ingestion

## Components Implemented

### 1. Backend Scraper: `loadDB/upcoming.py`
- **Purpose**: Collect and populate next 20 upcoming matches across 4 VCT 2026 Kickoff events
- **Sources** (hardcoded):
  - https://www.vlr.gg/event/2682/vct-2026-americas-kickoff
  - https://www.vlr.gg/event/2684/vct-2026-emea-kickoff
  - https://www.vlr.gg/event/2683/vct-2026-pacific-kickoff
  - https://www.vlr.gg/event/2685/vct-2026-china-kickoff

- **Workflow**:
  1. Collects candidate match IDs from tournament pages
  2. Fetches each match page to extract:
     - `match_ts_utc`: projected start time (ISO 8601 UTC)
     - `team_a`, `team_b`: team names (or "TBD" if unknown)
     - Tournament name, stage, match name
  3. Filters to future-only (UTC > now)
  4. Skips showmatches
  5. Upserts into `Matches` table with null scores (indicates not-yet-played)
  6. Limits to 20 soonest matches

- **Key Features**:
  - **Idempotent**: Safe to re-run; uses `ON CONFLICT(match_id)` to upsert
  - **Handles TBD**: Stores "TBD" when opponent name not confirmed
  - **Concurrency**: Uses semaphore-limited async HTTP for speed
  - **Robust**: Recovers from individual match fetch failures

- **Run**:
  ```bash
  python -m loadDB.upcoming
  ```
  Output: "Upserted N upcoming matches into DB."

### 2. API Endpoint: `frontend/app/api/upcoming-matches/route.js`
- **Purpose**: Serve upcoming matches from the database to the frontend
- **Limit**: 20 matches (configurable in `LIMIT` clause)
- **Returns**: JSON array with match metadata, team logos, tournament logos
- **Filtering**:
  - Queries `Matches` where date > today
  - Sorts by `match_ts_utc` ascending (soonest first)
  - Normalizes team names using existing aliases
  - Filters out showmatch teams (e.g., "Team International")
- **TBD Handling**: Returns team names as-is; frontend displays "TBD" with italic styling

### 3. Frontend Homepage: `frontend/app/page.js`
- **Fetch Flow**:
  1. Try `/api/vct-upcoming-matches` (live scrape, fallback)
  2. Fall back to `/api/upcoming-matches` (database, primary)
- **Display**:
  - Shows top 5 matches by default, with "View More" toggle
  - Renders TBD teams in lighter color (white/60) + italic font
  - Displays event logo, match date/time, tournament name
  - Links to match detail page
- **Enhancements Made**:
  - Added conditional styling for TBD teams (distinguishable from confirmed)
  - Already supports 20+ matches in database

## Database Schema (Matches Table)

Key columns used for upcoming matches:
```
- match_id: VLR match ID (primary key)
- tournament: Tournament name (e.g., "VCT 2026 Americas Kickoff")
- stage: Stage (e.g., "Winners Bracket", "Group Stage")
- match_type: "VCT" (for kickoff events)
- match_name: Human-readable match name
- team_a, team_b: Team names or "TBD"
- team_a_score, team_b_score: NULL (until match is played)
- match_ts_utc: ISO 8601 UTC timestamp (e.g., "2026-01-17T17:00:00Z")
- match_date: YYYY-MM-DD string
- match_result: Formatted result string
```

## Usage

### Run the Scraper (Manual)
```bash
python -m loadDB.upcoming
```

### Expected Output
```
Collecting upcoming matches for VCT 2026 Kickoff events...
Found 20 upcoming matches (pre-limit=20)
Upserted 20 upcoming matches into DB.
```

### Test Database
```bash
python -c "
import sqlite3
conn = sqlite3.connect('valorant_esports.db')
cur = conn.cursor()
cur.execute('''SELECT match_id, match_date, team_a, team_b FROM Matches 
              WHERE match_date > date('now') LIMIT 5''')
for row in cur.fetchall():
    print(f'Match {row[0]}: {row[2]} vs {row[3]} on {row[1]}')
cur.close()
"
```

### View Homepage (Next.js Dev)
```bash
cd frontend
npm run dev  # Visit http://localhost:3000
```

The upcoming matches section should display with:
- Next 5 upcoming matches visible
- "View More" button if more than 5 available
- TBD teams shown in light italic text
- Event logos and tournament names

## Future Enhancements

### Automated Scheduling (Post-MVP)
1. Set up a cron job or scheduler to run `python -m loadDB.upcoming` every 30–60 minutes
2. Auto-ingest matches 3 hours after projected start (when results likely available)
   - Query `Matches WHERE match_ts_utc < now() - interval('3 hours') AND team_a_score IS NULL`
   - Run `python -m loadDB.cli ingest [match_id]` for each
   - Update Elo snapshots

### Implementation Hooks
- Add a `processed` boolean column to track which matches have been auto-ingested
- Schedule via APScheduler, GitHub Actions, or server cron
- Re-run scraper before checking for ingestion to ensure fresh upcoming list

## Testing Results

Ran `python -m loadDB.upcoming` successfully:
- Collected 20 upcoming matches across 4 Kickoff events
- Inserted matches with:
  - Confirmed teams: NRG, Cloud9, MIBR, ENVY, G2 Esports, Sentinels, Natus Vincere, Karmine Corp, etc.
  - TBD teams: Where opponent not yet announced
  - Proper UTC timestamps (e.g., 2026-01-17T17:00:00Z)
- Database query confirmed matches stored with correct dates and team names

## Notes

- **No Server Required Yet**: Homepage displays upcoming matches from database; live scrape fallback available if needed
- **Idempotent Design**: Safe to run scraper on a timer without manual coordination
- **TBD Representation**: Stored as "TBD" in database; frontend displays with distinct styling
- **Match Links**: Upcoming matches link to detail pages; detail pages will show team info once ingested
- **Aliases**: Team names automatically normalized using existing `team-utils.js` aliases (consistent with rest of site)
