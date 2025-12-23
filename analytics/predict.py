import os
import sqlite3
from typing import Dict

import numpy as np
import joblib


MODELS_DIR = 'models'


class Predictor:
    def __init__(self, db_path: str = 'valorant_esports.db'):
        self.db_path = db_path
        self.match_model = None
        self.kills_model = None
        self._load_models()

    def _load_models(self):
        mm = os.path.join(MODELS_DIR, 'match_outcome.pkl')
        km = os.path.join(MODELS_DIR, 'player_kills.pkl')
        if os.path.exists(mm):
            self.match_model = joblib.load(mm)
        if os.path.exists(km):
            self.kills_model = joblib.load(km)

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def team_elos(self) -> Dict[str, float]:
        con = self._connect()
        cur = con.cursor()
        cur.execute("SELECT team_name, COALESCE(team_elo, 1500.0) FROM Teams")
        m = {n: float(e) for n, e in cur.fetchall()}
        con.close()
        return m

    def player_elos(self) -> Dict[str, float]:
        con = self._connect()
        cur = con.cursor()
        cur.execute("SELECT player_name, COALESCE(player_elo, 1500.0) FROM Players")
        m = {n: float(e) for n, e in cur.fetchall()}
        con.close()
        return m

    def predict_match(self, team1_name: str, team2_name: str):
        teams = self.team_elos()
        r1 = teams.get(team1_name)
        r2 = teams.get(team2_name)
        if r1 is None or r2 is None or self.match_model is None:
            return {
                'team1_name': team1_name,
                'team2_name': team2_name,
                'team1_elo': r1,
                'team2_elo': r2,
                'team1_win_prob': None
            }
        x = np.array([[r1, r2, r1 - r2]])
        prob = float(self.match_model.predict_proba(x)[:, 1][0])
        return {
            'team1_name': team1_name,
            'team2_name': team2_name,
            'team1_elo': r1,
            'team2_elo': r2,
            'team1_win_prob': prob
        }

    def predict_kills(self, player_name: str):
        con = self._connect()
        cur = con.cursor()
        cur.execute("SELECT player_id, COALESCE(player_elo, 1500.0) FROM Players WHERE player_name = ?", (player_name,))
        row = cur.fetchone()
        con.close()
        if row is None or self.kills_model is None:
            return {'player_name': player_name, 'expected_kills': None}
        pid, p_elo = int(row[0]), float(row[1])
        # Use neutral baseline context (zeros) with elo feature
        x = np.array([[p_elo, 0, 0, 0, 1.0, 0, 0, 0]])
        y = float(self.kills_model.predict(x)[0])
        return {'player_name': player_name, 'player_elo': p_elo, 'expected_kills': y}
