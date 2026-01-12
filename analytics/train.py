import os
import sqlite3
from typing import List, Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, r2_score, mean_absolute_error
import joblib

from .elo import DEFAULT_TEAM_ELO, DEFAULT_PLAYER_ELO, expected_score, update_rating


DB_PATH = 'valorant_esports.db'
MODELS_DIR = 'models'


def ensure_models_dir():
    """Create models directory if it doesn't exist."""
    os.makedirs(MODELS_DIR, exist_ok=True)


def collect_datasets(db_path: str = DB_PATH):
    """
    Collect training datasets by iterating matches chronologically and computing Elo ratings.
    
    Builds datasets for both match outcome prediction and player performance prediction.
    Elo ratings are computed incrementally as matches are processed.
    
    Args:
        db_path: Path to database file
    
    Returns:
        Tuple of (match_df, player_df) DataFrames with features and targets
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute("SELECT match_id, team1_name, team2_name, team1_score, team2_score FROM Matches ORDER BY match_id ASC")
    matches = cur.fetchall()

    team_elo: Dict[str, float] = {}
    player_elo: Dict[int, float] = {}

    match_rows: List[Dict] = []
    player_rows: List[Dict] = []

    for match_id, t1, t2, s1, s2 in matches:
        r1 = team_elo.get(t1, DEFAULT_TEAM_ELO)
        r2 = team_elo.get(t2, DEFAULT_TEAM_ELO)
        match_rows.append({
            'match_id': match_id,
            'team1_name': t1,
            'team2_name': t2,
            'team1_elo_pre': r1,
            'team2_elo_pre': r2,
            'elo_diff': r1 - r2,
            'team1_win': 1 if (s1 is not None and s2 is not None and s1 > s2) else 0
        })

        cur.execute(
            """
            SELECT ps.player_id, ps.kills, ps.deaths, ps.assists, ps.acs, ps.rating, ps.adr, ps.fk, ps.fd
            FROM Player_Stats ps
            WHERE ps.match_id = ? AND ps.map_id IS NULL
            """,
            (match_id,)
        )
        for pid, kills, deaths, assists, acs, rating, adr, fk, fd in cur.fetchall():
            p_elo = player_elo.get(pid, DEFAULT_PLAYER_ELO)
            player_rows.append({
                'match_id': match_id,
                'player_id': pid,
                'player_elo_pre': p_elo,
                'kills': int(kills) if kills is not None else 0,
                'deaths': int(deaths) if deaths is not None else 0,
                'assists': int(assists) if assists is not None else 0,
                'acs': float(acs) if acs is not None else 0.0,
                'rating': float(rating) if rating is not None else 0.0,
                'adr': float(adr) if adr is not None else 0.0,
                'fk': int(fk) if fk is not None else 0,
                'fd': int(fd) if fd is not None else 0,
            })

        if s1 is None or s2 is None:
            continue
        winner = 1 if s1 > s2 else 2
        exp1 = 1.0 / (1.0 + 10.0 ** (-(r1 - r2) / 400.0))
        exp2 = 1.0 - exp1
        score1 = 1.0 if winner == 1 else 0.0
        score2 = 1.0 - score1
        r1_post = update_rating(r1, score1, exp1, 32.0)
        r2_post = update_rating(r2, score2, exp2, 32.0)
        team_elo[t1] = r1_post
        team_elo[t2] = r2_post

        cur.execute("SELECT player_id, rating FROM Player_Stats WHERE match_id = ? AND map_id IS NULL", (match_id,))
        rows = cur.fetchall()
        team_avg = np.mean([float(r or 1.0) for _, r in rows]) if rows else 1.0
        for pid, rating in rows:
            pre = player_elo.get(pid, DEFAULT_PLAYER_ELO)
            scale = float(rating or 1.0) / (team_avg or 1.0)
            k_eff = max(8.0, min(24.0 * scale, 48.0))
            res = score1
            post = update_rating(pre, res, 0.5, k_eff)
            player_elo[pid] = post

    con.close()
    return pd.DataFrame(match_rows), pd.DataFrame(player_rows)


def train_and_save():
    """
    Train and save machine learning models for match outcome and player performance prediction.
    
    Trains:
    - Match outcome classifier (LogisticRegression) using team Elo ratings
    - Player kills regressor (RandomForestRegressor) using player Elo and stats
    
    Models are saved to the models directory with associated metrics files.
    Falls back to minimal models if insufficient training data is available.
    """
    ensure_models_dir()
    df_match, df_player = collect_datasets()

    match_feats = df_match[['team1_elo_pre', 'team2_elo_pre', 'elo_diff']].values
    match_target = df_match['team1_win'].values
    if len(df_match) >= 20 and match_target.sum() > 0 and match_target.sum() < len(match_target):
        X_tr, X_te, y_tr, y_te = train_test_split(match_feats, match_target, test_size=0.2, random_state=42, stratify=match_target)
        clf = LogisticRegression(max_iter=1000)
        clf.fit(X_tr, y_tr)
        y_prob = clf.predict_proba(X_te)[:, 1]
        acc = accuracy_score(y_te, (y_prob >= 0.5).astype(int))
        try:
            auc = roc_auc_score(y_te, y_prob)
        except Exception:
            auc = float('nan')
        joblib.dump(clf, os.path.join(MODELS_DIR, 'match_outcome.pkl'))
        with open(os.path.join(MODELS_DIR, 'match_outcome.metrics.txt'), 'w') as f:
            f.write(f"accuracy={acc:.4f}\nauc={auc:.4f}\n")
    else:
        clf = LogisticRegression(max_iter=1)
        X = np.array([[0, 0, 0], [100, -100, 200]])
        y = np.array([0, 1])
        clf.fit(X, y)
        joblib.dump(clf, os.path.join(MODELS_DIR, 'match_outcome.pkl'))

    if len(df_player) >= 50:
        feat_cols = ['player_elo_pre', 'deaths', 'assists', 'acs', 'rating', 'adr', 'fk', 'fd']
        X = df_player[feat_cols].values
        y = df_player['kills'].values
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
        reg = RandomForestRegressor(n_estimators=200, random_state=42)
        reg.fit(X_tr, y_tr)
        y_pred = reg.predict(X_te)
        r2 = r2_score(y_te, y_pred)
        mae = mean_absolute_error(y_te, y_pred)
        joblib.dump(reg, os.path.join(MODELS_DIR, 'player_kills.pkl'))
        with open(os.path.join(MODELS_DIR, 'player_kills.metrics.txt'), 'w') as f:
            f.write(f"r2={r2:.4f}\nmae={mae:.4f}\n")
    else:
        reg = RandomForestRegressor(n_estimators=10, random_state=42)
        reg.fit(np.zeros((2, 8)), np.array([10.0, 15.0]))
        joblib.dump(reg, os.path.join(MODELS_DIR, 'player_kills.pkl'))


if __name__ == '__main__':
    train_and_save()
