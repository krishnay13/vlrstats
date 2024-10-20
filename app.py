# app.py

from flask import Flask, g, render_template
import sqlite3

app = Flask(__name__)

DATABASE = 'valorant_esports.db'


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


if __name__ == '__main__':
    app.run(debug=True)
