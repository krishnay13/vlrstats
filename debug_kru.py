#!/usr/bin/env python3
import json
import sqlite3

# Check what's in the aliases
with open('loadDB/aliases/teams.json', 'r', encoding='utf-8') as f:
    aliases = json.load(f)
    print('Aliases with kru/krü:')
    for k, v in aliases.items():
        if 'kru' in k.lower() or 'krü' in k.lower():
            print(f'  {repr(k)} -> {repr(v)}')

# Check what's in the database
conn = sqlite3.connect('valorant_esports.db')
cursor = conn.cursor()
cursor.execute('SELECT DISTINCT team FROM Player_Stats WHERE team LIKE "%KR%" OR team LIKE "%kr%"')
teams = cursor.fetchall()
print('\nTeams in DB with KR or kr:')
for (team,) in teams:
    print(f'  {repr(team)} -> lowercase: {repr(team.lower())}')
conn.close()
