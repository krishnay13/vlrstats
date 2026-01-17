import sqlite3

conn = sqlite3.connect('valorant_esports.db')
rows = conn.execute("""
    SELECT match_id, team_a, team_b, team_a_score, team_b_score 
    FROM Matches 
    WHERE match_date >= '2026-01-01' AND team_a_score IS NOT NULL 
    ORDER BY match_date
""").fetchall()

print("2026 matches with scores:")
for row in rows:
    print(f"  {row[0]}: {row[1]} {row[3]}-{row[4]} {row[2]}")

conn.close()
