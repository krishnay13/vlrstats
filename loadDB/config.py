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

# Elo defaults (tweak here to tune system)
START_ELO = 1500.0
K_BASE = 25.0

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
