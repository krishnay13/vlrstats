# Make loadDB a package and expose key entrypoints
from .config import DB_PATH, TEAM_ALIASES
from .elo import compute_elo
from .vlr_ingest import ingest
