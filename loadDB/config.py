import json
import os

# Base paths
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(REPO_ROOT, 'valorant_esports.db')

# Team alias configuration
ALIASES_FILE = os.path.join(os.path.dirname(__file__), 'aliases.json')


def _load_aliases() -> dict[str, str]:
    default_aliases = {
        'guangzhou huadu bilibili gaming(bilibili gaming)': 'Bilibili Gaming',
        'guangzhou huadu bilibili gaming': 'Bilibili Gaming',
        'bilibili gaming': 'Bilibili Gaming',
        'g2': 'G2 Esports',
        'tl': 'Team Liquid',
        'fnc': 'FNATIC',
        't1': 'T1',
        'sen': 'Sentinels',
        'rrq': 'Rex Regum Qeon',
        'prx': 'Paper Rex',
        'edg': 'EDward Gaming',
        'drx': 'DRX',
        'blg': 'Bilibili Gaming',
        'mibr': 'MIBR',
        'xlg': 'Xi Lai Gaming',
        'th': 'Team Heretics',
        'gx': 'GIANTX',
        'nrg': 'NRG',
        'loud': 'LOUD',
        'kru': 'KRÜ Esports',
        'kru esports': 'KRÜ Esports',
        'visa kru': 'KRÜ Esports',
        'visa kru esports': 'KRÜ Esports',
    }
    try:
        if os.path.exists(ALIASES_FILE):
            with open(ALIASES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # ensure keys are lowercase for lookups
                    return {str(k).lower(): str(v) for k, v in data.items()}
    except Exception:
        pass
    return default_aliases


TEAM_ALIASES: dict[str, str] = _load_aliases()

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
