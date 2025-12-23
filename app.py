# app.py

from flask import Flask, g, render_template, jsonify, request
import sqlite3
from analytics.elo import EloEngine
from analytics.predict import Predictor

app = Flask(__name__)

DATABASE = 'valorant_esports.db'
elo_engine = EloEngine(DATABASE)
predictor = Predictor(DATABASE)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/')
def index():
    return "Welcome to the Valorant Esports Stats Portal!"


@app.route('/matches')
def show_matches():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM Matches')
    matches = cursor.fetchall()
    return render_template('matches.html', matches=matches)


@app.route('/teams')
def show_teams():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM Teams')
    teams = cursor.fetchall()

    # Fetch player names
    team_data = []
    for team in teams:
        player_ids = team[2:7]
        player_names = []
        for pid in player_ids:
            if pid:
                cursor.execute('SELECT player_name FROM Players WHERE player_id = ?', (pid,))
                pname = cursor.fetchone()
                player_names.append(pname[0] if pname else 'Unknown')
        team_data.append((team[0], team[1], player_names))

    return render_template('teams.html', teams=team_data)


@app.route('/players')
def show_players():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM Players')
    players = cursor.fetchall()
    return render_template('players.html', players=players)


@app.route('/match/<int:match_id>')
def match_details(match_id):
    db = get_db()
    cursor = db.cursor()

    # Get match info
    cursor.execute('SELECT * FROM Matches WHERE match_id = ?', (match_id,))
    match = cursor.fetchone()

    if match is None:
        return "Match not found", 404

    # Get maps associated with the match
    cursor.execute('SELECT * FROM Maps WHERE match_id = ?', (match_id,))
    maps = cursor.fetchall()

    # Get player stats for the match
    cursor.execute('SELECT * FROM Player_Stats WHERE match_id = ? AND map_id IS NULL', (match_id,))
    player_stats = cursor.fetchall()

    return render_template('match_details.html', match=match, maps=maps, player_stats=player_stats)


# --- API: Elo & Predictions ---
@app.route('/api/elo/recalculate', methods=['POST'])
def api_recalculate_elo():
    elo_engine.recalc_from_history()
    # Reload predictor state to see updated elos
    global predictor
    predictor = Predictor(DATABASE)
    return jsonify({"status": "ok"})


@app.route('/api/elo/teams')
def api_elo_teams():
    con = get_db()
    cur = con.cursor()
    cur.execute('SELECT team_name, COALESCE(team_elo, 1500.0) FROM Teams ORDER BY team_elo DESC')
    rows = cur.fetchall()
    return jsonify([{'team_name': r[0], 'team_elo': r[1]} for r in rows])


@app.route('/api/elo/players')
def api_elo_players():
    con = get_db()
    cur = con.cursor()
    cur.execute('SELECT player_name, team_name, COALESCE(player_elo, 1500.0) FROM Players ORDER BY player_elo DESC LIMIT 200')
    rows = cur.fetchall()
    return jsonify([{'player_name': r[0], 'team_name': r[1], 'player_elo': r[2]} for r in rows])


@app.route('/api/predict/match', methods=['POST'])
def api_predict_match():
    data = request.get_json(force=True)
    t1 = data.get('team1_name')
    t2 = data.get('team2_name')
    if not t1 or not t2:
        return jsonify({'error': 'team1_name and team2_name required'}), 400
    res = predictor.predict_match(t1, t2)
    return jsonify(res)


@app.route('/api/predict/kills', methods=['POST'])
def api_predict_kills():
    data = request.get_json(force=True)
    pname = data.get('player_name')
    if not pname:
        return jsonify({'error': 'player_name required'}), 400
    res = predictor.predict_kills(pname)
    return jsonify(res)


if __name__ == '__main__':
    app.run(debug=True)
