# Quick Start: Upcoming Matches Feature

## What's New

The VCT homepage now displays the **next 20 upcoming matches** from the VCT 2026 Kickoff events (Americas, EMEA, Pacific, China). Matches with unannounced opponents show "TBD" in italic text.

## How It Works

### Data Flow
1. **Backend Scraper** (`loadDB/upcoming.py`) 
   - Collects next 20 matches from 4 Kickoff events
   - Extracts team names and projected start times
   - Stores in the `Matches` table

2. **API Endpoint** (`frontend/app/api/upcoming-matches/route.js`)
   - Serves matches from database
   - Returns top 20 future matches sorted by time

3. **Frontend Homepage** (`frontend/app/page.js`)
   - Displays top 5 matches, "View More" to see all
   - TBD teams shown in lighter italic text
   - Clickable to match detail pages

## Setup

### Step 1: Install Dependencies (if needed)
```bash
pip install -r requirements.txt
npm install  # In frontend/ directory
```

### Step 2: Populate Upcoming Matches
```bash
python -m loadDB.upcoming
```

Output:
```
Collecting upcoming matches for VCT 2026 Kickoff events...
Found 20 upcoming matches (pre-limit=20)
Upserted 20 upcoming matches into DB.
```

### Step 3: Verify in Database (Optional)
```bash
python -c "
import sqlite3
conn = sqlite3.connect('valorant_esports.db')
cur = conn.cursor()
cur.execute('''SELECT COUNT(*) FROM Matches WHERE match_date > date('now')''')
count = cur.fetchone()[0]
print(f'Upcoming matches in DB: {count}')
cur.close()
"
```

### Step 4: Run the Frontend
```bash
cd frontend
npm run dev  # or yarn dev / pnpm dev
# Visit http://localhost:3000
```

The **Upcoming Matches** section on the homepage should now display the next 20 matches with:
- Team names (or "TBD")
- Event names and logos
- Match date/time
- Regional representation

## Usage

### Manual Refresh (One-Time)
```bash
python -m loadDB.upcoming
```

### Scheduled Refresh (Future)
Set up a cron job to run periodically:
```bash
# Every 30 minutes
*/30 * * * * cd /path/to/vlrstats && python -m loadDB.upcoming >> /tmp/upcoming.log 2>&1

# Every 1 hour
0 * * * * cd /path/to/vlrstats && python -m loadDB.upcoming >> /tmp/upcoming.log 2>&1
```

Or use a Python scheduler like APScheduler in your app.

## TBD Handling

When an opponent isn't announced yet:
- **Database**: Stored as `team_a = "TBD"` or `team_b = "TBD"`
- **Frontend**: Displayed in lighter gray italic text to distinguish from confirmed teams
- **Match Links**: Still clickable; detail page shows available info

Once the opponent is confirmed:
1. Re-run `python -m loadDB.upcoming` to update
2. Or manually ingest the match once it's played with `python -m loadDB.cli ingest <match_id>`

## Testing

### Verify API Endpoint
```bash
curl http://localhost:3000/api/upcoming-matches
```

Expected response:
```json
[
  {
    "match_id": 596402,
    "team_a": "NRG",
    "team_b": "Cloud9",
    "match_date": "2026-01-17",
    "match_ts_utc": "2026-01-17T17:00:00Z",
    "tournament": "VCT 2026: Americas Kickoff",
    "stage": "Winners Bracket",
    ...
  },
  ...
]
```

### Check Database
```bash
python -c "
import sqlite3
conn = sqlite3.connect('valorant_esports.db')
cur = conn.cursor()
cur.execute('''
SELECT match_id, team_a, team_b, match_ts_utc 
FROM Matches 
WHERE match_date > date('now')
ORDER BY match_ts_utc ASC
LIMIT 3
''')
for row in cur.fetchall():
    print(f'Match {row[0]}: {row[1]} vs {row[2]} at {row[3]}')
cur.close()
"
```

## Future Enhancements

### Automatic Ingestion (Post-MVP)
After 3 hours past the projected start time, automatically ingest match results:
```python
# Pseudo-code
matches_to_ingest = query(
    "SELECT match_id FROM Matches 
     WHERE match_ts_utc < NOW() - INTERVAL 3 HOURS 
     AND team_a_score IS NULL"
)
for match_id in matches_to_ingest:
    ingest_match(match_id)
    update_elo()
```

Requires:
- Server running (currently you have local dev only)
- APScheduler or similar task queue
- `processed` flag column to track ingested matches

## Files Modified

1. **`loadDB/upcoming.py`** (NEW)
   - Scraper for collecting upcoming matches

2. **`frontend/app/api/upcoming-matches/route.js`**
   - Already had `LIMIT 20` and TBD handling

3. **`frontend/app/page.js`**
   - Added conditional styling for TBD teams (light italic text)

4. **`README.md`**
   - Added Section 3 with upcoming matches instructions

## Troubleshooting

### No Matches Showing on Homepage
1. Verify matches are in DB:
   ```bash
   python -c "import sqlite3; conn = sqlite3.connect('valorant_esports.db'); print(conn.execute('SELECT COUNT(*) FROM Matches WHERE match_date > date(\"now\")').fetchone())"
   ```
2. Check API response:
   ```bash
   curl http://localhost:3000/api/upcoming-matches | python -m json.tool
   ```
3. Check browser console for fetch errors

### All Matches Are TBD
- This is expected if opponents haven't been announced yet
- Re-run `python -m loadDB.upcoming` as tournaments progress

### Matches Aren't Updating
- Scraper only pulls from 4 hardcoded Kickoff events
- Run manually or set up a cron job
- Consider expanding to other VCT events in the future

## Contact / Support

See `UPCOMING_MATCHES_IMPLEMENTATION.md` for technical details and architecture notes.
