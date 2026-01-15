import os

# Base paths
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(REPO_ROOT, 'valorant_esports.db')

# Use unified alias system
from .aliases import get_all_aliases, normalize_team

# Load all aliases
_ALL_ALIASES = get_all_aliases()

# Team aliases (for backward compatibility)
TEAM_ALIASES: dict[str, str] = _ALL_ALIASES.get('team', {})

# Legacy aliases file path (moved to _backup/aliases.json)
# New aliases are in aliases/ directory
ALIASES_FILE = os.path.join(os.path.dirname(__file__), 'aliases', 'teams.json')

# Elo defaults (tune these to change system behaviour)

# --- Team Elo core ---
START_ELO = 1500.0

# Base K-factor for team Elo (before importance / MOV / recency adjustments)
K_BASE = 25.0

# --- Margin-of-victory (MOV) tuning ---
# Classic Elo MOV adjustment: ln(1+margin) * MOV_BASE / (|rdiff|*MOV_RDIFF_SCALE + MOV_BASE)
# Adjust these if blowouts feel too strong / too weak.
MOV_BASE = 2.2
MOV_RDIFF_SCALE = 0.001

# Round-margin normalisation (used when map scores are available)
# We currently:
#   - compute average round margin per map
#   - divide by ROUND_MARGIN_DIVISOR
#   - clamp to [ROUND_MARGIN_MIN, ROUND_MARGIN_MAX]
ROUND_MARGIN_DIVISOR = 2.0
ROUND_MARGIN_MIN = 1.0
ROUND_MARGIN_MAX = 8.0

# Optional extra weight for longer series based on maps played.
# Effective margin is multiplied by: (1 + ROUND_MARGIN_MAPS_BONUS * max(0, maps_played - 1))
# Default 0.0 keeps current behaviour; increase slowly (e.g. 0.1–0.2) if BO3/BO5
# should matter more than BO1s.
ROUND_MARGIN_MAPS_BONUS = 0.0

# --- Tournament / match importance weights ---
# Competition tier weights
IMP_CHAMPIONS = 2.0
IMP_MASTERS_BASE = 1.8
IMP_MASTERS_BANGKOK = 1.7
IMP_MASTERS_TORONTO = 1.9

# Default regional VCT / domestic league weight
IMP_REGIONAL = 1.0

# Secondary circuits / offseason events
IMP_VCL = 0.9
IMP_OFFSEASON = 0.8
IMP_SHOWMATCH = 0.3  # if ever factored into Elo, keep much lower impact

# Bracket / match-context weights (multiply on top of competition tier)
IMP_MATCH_GRAND_FINAL = 1.45
IMP_MATCH_FINALS_UPPER_LOWER = 1.35
IMP_MATCH_SEMIFINAL = 1.30
IMP_MATCH_QUARTERFINAL = 1.25
IMP_MATCH_PLAYOFF = 1.15
IMP_MATCH_ELIM_DECIDER = 1.10
IMP_MATCH_GROUP_OR_SWISS = 1.00

# --- Player Elo core ---
PLAYER_START_ELO = 1500.0
K_PLAYER_BASE = 18.0
PLAYER_INFLUENCE_BETA = 0.15
PLAYER_WEIGHT_EQUAL_BLEND = 0.5
PLAYER_MAX_SHARE_FRACTION = 0.35
RATING_RELATIVE_CLIP_LOW = 0.6
RATING_RELATIVE_CLIP_HIGH = 1.3
PLAYER_RATING_WEIGHT = 0.85
PLAYER_ACS_WEIGHT = 0.15
PLAYER_PERF_LOGIT_BETA = 4.0
WIN_LOSS_WEIGHT = 0.05
PLAYER_DELTA_CAP = 20.0
PLAYER_SEED_SCALE = 100.0
