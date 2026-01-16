import sqlite3

conn = sqlite3.connect('valorant_esports.db')
cur = conn.cursor()

# Update all upcoming matches to have NULL scores
cur.execute("""
    UPDATE Matches 
    SET team_a_score = NULL, team_b_score = NULL 
    WHERE match_ts_utc IS NOT NULL 
    AND datetime(match_ts_utc, '+5 hours') > datetime('now')
""")

affected = cur.rowcount
conn.commit()
conn.close()

print(f'Cleaned {affected} upcoming matches by setting scores to NULL')
