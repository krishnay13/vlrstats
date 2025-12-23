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

### 2. Scrape Fresh 2025 Data
```bash
# Scrape latest VCT 2025 matches
python loadDB/scrape_2025_fresh.py

# This creates: loadDB/matches_2025.txt
```

### 3. Load Data into Database
```bash
# Process scraped matches
python loadDB/LoadStats.py

# Or reset and start fresh
python reset_db_2025.py
```

### 4. Build Elo Ratings
```bash
# Recalculate Elo from match history
python -c "from analytics.elo import EloEngine; EloEngine().recalc_from_history()"
```

### 5. Train ML Models
```bash
python -m analytics.train
```

### 6. Run API Server
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
│   ├── scrape_2025_fresh.py       # VCT 2025 scraper (improved)
│   ├── LoadStats.py               # Load matches into DB
│   ├── db_init.py                 # Database schema
│   ├── MatchScraper.py            # Tournament scraper
│   ├── main.py                    # URL preprocessing
│   ├── matches_2025.txt           # Scraped match URLs
│   ├── matches.txt                # Legacy match IDs
│   └── full_matches.txt           # Legacy full URLs
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