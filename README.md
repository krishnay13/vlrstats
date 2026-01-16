# VLR Stats: Elo + ML System

**Status**: 🚧 Fresh Start for 2025 VCT Season

Valorant esports statistics platform with **Elo rating system** and **ML-based match predictions**.

## Features

- **Team & Player Elo Ratings** — Dynamic rating system tracking performance over time
- **Match Outcome Predictions** — ML models for win probability
- **Player Performance Predictions** — Expected kills/stats per match
- **REST API** — Query rankings and get predictions
- **2025 VCT Data** — Fresh scraping from vlr.gg (no official API)

## Quick Start

### 1. Setup Environment
```bash
pip install -r requirements.txt
```

### 2. Ingest Matches

#### Ingest Individual Matches (Easiest Method)
```bash
# Ingest by match IDs from vlr.gg
python -m loadDB.cli ingest 596398

# Ingest by full URLs
python -m loadDB.cli ingest https://www.vlr.gg/596398/loud-vs-cloud9-vct-2026-americas-kickoff-ur1

# Ingest multiple matches at once
python -m loadDB.cli ingest 596398 596399 596400
```

**Note**: After ingestion, Elo ratings are automatically recalculated and stored for all years (2024, 2025, 2026, all-time).

#### Scrape Tournament Matches
```bash
# Scrape all completed match IDs from a tournament
python -m loadDB.cli scrape-tournament https://www.vlr.gg/event/2792

# Save to a custom file
python -m loadDB.cli scrape-tournament https://www.vlr.gg/event/2792 -o my_tournament_matches.txt

# Include all matches (not just completed ones)
python -m loadDB.cli scrape-tournament https://www.vlr.gg/event/2792 --all
```

#### Upload Matches from File
```bash
# Upload matches from a file with tournament type (interactive prompt)
python -m loadDB.cli upload-from-file tournament_matches.txt

# Upload with tournament type specified
python -m loadDB.cli upload-from-file tournament_matches.txt --tournament-type VCL
python -m loadDB.cli upload-from-file tournament_matches.txt --tournament-type VCT
python -m loadDB.cli upload-from-file tournament_matches.txt --tournament-type OFFSEASON
```

**Tournament Types:**
- `VCL` - Valorant Challengers League
- `VCT` - Valorant Champions Tour
- `OFFSEASON` - Offseason tournaments

### 3. Populate Upcoming Matches (Next 20)

The frontend displays upcoming matches that are stored in the `Matches` table. To populate the next 20 matches from the VCT 2026 Kickoff events:

```bash
# Scrape and populate the next 20 upcoming matches
python -m loadDB.upcoming

# This command:
# - Fetches from 4 VCT 2026 Kickoff events (Americas, EMEA, Pacific, China)
# - Collects match IDs and projected start times
# - Stores TBD for unknown opponent names (can be revealed after ingestion)
# - Upserts into the Matches table with null scores until completion
# - Idempotent—safe to re-run periodically (e.g., every 30–60 minutes)

# Run this regularly to keep the upcoming matches fresh on the homepage
```

### 4. Build Elo Ratings
```bash
# Compute Elo (prints top teams). Use --save to persist snapshots/history
python -m loadDB.cli elo compute --top 20 --save
```

### 4. Build Elo Ratings
```bash
# Compute Elo (prints top teams). Use --save to persist snapshots/history
python -m loadDB.cli elo compute --top 20 --save
```

### 5. Display Rankings
```bash
python -m loadDB.cli show top-teams -n 20
python -m loadDB.cli show top-players -n 20
python -m loadDB.cli show team-history "G2 Esports"
python -m loadDB.cli show player-history "trent"
```

### 5. Display Rankings
```bash
python -m loadDB.cli show top-teams -n 20
python -m loadDB.cli show top-players -n 20
python -m loadDB.cli show team-history "G2 Esports"
python -m loadDB.cli show player-history "trent"
```

### 6. Train ML Models
```bash
python -m analytics.train
```

### 6. Train ML Models
```bash
python -m analytics.train
```

### 7. Run API Server
```bash
python app.py
# Server runs on http://127.0.0.1:5000
```

## API Endpoints

### Team & Player Rankings
```
GET /api/elo/teams              # Top teams by Elo
GET /api/elo/players            # Top players by Elo
```

### Predictions
```
POST /api/predict/match         # Match outcome probability
Body: {"team1_name": "FNATIC", "team2_name": "DRX"}

POST /api/predict/kills         # Expected player kills
Body: {"player_name": "Alfajer"}
```

### Utilities
```
POST /api/elo/recalculate      # Rebuild all Elo ratings
```

## Project Structure

```
.
├── app.py                          # Flask API server
├── valorant_esports.db            # SQLite database
├── requirements.txt               # Dependencies
├── reset_db_2025.py               # Database reset utility
├── README.md
│
├── analytics/                      # Elo & ML engine
│   ├── elo.py                     # Elo calculation & history
│   ├── train.py                   # Model training
│   └── predict.py                 # Inference
│
├── loadDB/                         # Data scraping & loading
│   ├── cli.py                     # Unified CLI (ingest, elo, show, scrape-tournament, upload-from-file)
│   ├── config.py                  # Central config (DB path, Elo constants, aliases)
│   ├── aliases.json               # Team alias normalization map
│   ├── vlr_ingest.py              # Ingest single matches by ID/URL
│   ├── tournament_scraper.py     # Scrape match IDs from tournament pages
│   ├── db_utils.py                # Upsert helpers and schema ensure
│   ├── elo.py                     # Team/Player Elo computation
│   ├── display.py                 # Read-only display helpers
│   ├── backfill.py                # Timestamp backfill scaffold
│   ├── db_cleanup.py              # Drop legacy tables (if any)
│   └── _legacy/                   # Archived legacy utilities (deprecated)
│
├── models/                         # Trained ML models
│   ├── match_outcome.pkl
│   └── player_kills.pkl
│
├── frontend/                       # Next.js UI (optional)
│   └── ...
│
├── static/                         # Legacy Flask static files
└── templates/                      # Legacy Flask templates
```

## How It Works

### Elo System
- **Team Elo**: Updated after each match using Glicko-inspired formula (K=32)
- **Player Elo**: Scaled K-factor (8–48) based on performance vs team average
- **Expected Score**: `E = 1 / (1 + 10^(-(R_a - R_b)/400))`
- **Rating Update**: `R_new = R_old + K * (actual - expected)`

### ML Models
- **Match Outcome**: Logistic Regression using team Elo features
- **Player Kills**: Random Forest (200 trees) using player stats + Elo

### Data Pipeline
1. Scrape matches from vlr.gg (BeautifulSoup)
2. Parse team names, scores, player stats
3. Load into SQLite database
4. Calculate Elo ratings chronologically
5. Train ML models on feature-engineered dataset
6. Serve predictions via REST API

## Database Entry Commands Reference

### Match Ingestion

**Single Match Ingestion:**
```bash
# By match ID
python -m loadDB.cli ingest 123456

# By URL
python -m loadDB.cli ingest https://www.vlr.gg/123456/match-name

# Multiple matches
python -m loadDB.cli ingest 123456 123789 123890
```

**Tournament Scraping:**
```bash
# Scrape completed matches from a tournament
python -m loadDB.cli scrape-tournament https://www.vlr.gg/event/2792

# Custom output file
python -m loadDB.cli scrape-tournament https://www.vlr.gg/event/2792 -o matches.txt

# Include all matches (completed and upcoming)
python -m loadDB.cli scrape-tournament https://www.vlr.gg/event/2792 --all

# Scrape ALL VCT 2024 & 2025 matches (clears DB first!)
python -m loadDB.cli scrape-all-vct
```

**Batch Upload from File:**
```bash
# Interactive tournament type selection
python -m loadDB.cli upload-from-file tournament_matches.txt

# Specify match type directly
python -m loadDB.cli upload-from-file tournament_matches.txt --match-type VCL
python -m loadDB.cli upload-from-file tournament_matches.txt --match-type VCT
python -m loadDB.cli upload-from-file tournament_matches.txt --match-type OFFSEASON
python -m loadDB.cli upload-from-file tournament_matches.txt --match-type SHOWMATCH
```

### Elo Rating Commands

**Compute Elo Ratings:**
```bash
# Compute and display top 20 teams (no persistence)
python -m loadDB.cli elo compute --top 20

# Compute and save to database
python -m loadDB.cli elo compute --save --top 20
```

**View Rankings:**
```bash
# Top teams
python -m loadDB.cli show top-teams -n 20

# Top players
python -m loadDB.cli show top-players -n 20

# Team Elo history
python -m loadDB.cli show team-history "G2 Esports"

# Player Elo history
python -m loadDB.cli show player-history "trent"
```

### Database Schema

The `Matches` table includes:
- `match_id` (PRIMARY KEY)
- `tournament` - Tournament name
- `stage` - Stage (e.g., "Group Stage", "Playoffs")
- `match_type` - Match type (e.g., "Regular Season")
- `match_name` - Full match name
- `team_a`, `team_b` - Team names
- `team_a_score`, `team_b_score` - Match scores
- `match_result` - Formatted result string
- `match_ts_utc` - UTC timestamp
- `match_date` - Date string
- `match_type` - VCL, VCT, OFFSEASON, or SHOWMATCH (classification of match, not tournament)

## Known Issues & Improvements

### Current Limitations
- No official VLR.gg API (web scraping required)
- Team name parsing edge cases (e.g., "Gen.G EDward Gaming" merged teams)
- Stats extraction depends on HTML structure stability
- Historical 2024 data had quality issues (now cleared)

### Planned Enhancements
- [ ] Daily automated scraping of new matches
- [ ] Online learning (update Elo in real-time)
- [ ] Map-specific predictions
- [ ] Agent/role features for models
- [ ] Recent form tracking (rolling averages)
- [ ] Web UI for rankings and predictions

---

**Last Updated**: December 23, 2025 — Fresh start for 2025 VCT season