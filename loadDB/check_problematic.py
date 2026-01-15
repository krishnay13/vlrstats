"""Check problematic matches in database to identify patterns."""
from .db_utils import get_conn

conn = get_conn()
cur = conn.cursor()

# Get all problematic matches
cur.execute("""
    SELECT m.match_id, m.team_a, m.team_b, m.team_a_score, m.team_b_score,
           COUNT(DISTINCT mp.id) as map_count,
           COUNT(DISTINCT CASE WHEN mp.team_a_score IS NOT NULL AND mp.team_b_score IS NOT NULL THEN mp.id END) as maps_with_scores
    FROM Matches m
    LEFT JOIN Maps mp ON m.match_id = mp.match_id
    WHERE (m.team_a_score = m.team_b_score AND m.team_a_score > 0)
       OR (m.team_a_score > 0 AND m.team_a_score < 2 AND m.team_b_score = 0)
       OR (m.team_b_score > 0 AND m.team_b_score < 2 AND m.team_a_score = 0)
    GROUP BY m.match_id
    ORDER BY m.match_id
    LIMIT 20
""")

print("Problematic Matches:")
print("=" * 100)
for row in cur.fetchall():
    match_id, team_a, team_b, a_score, b_score, map_count, maps_with_scores = row
    print(f"Match {match_id}: {team_a} vs {team_b}")
    print(f"  Score: {a_score}-{b_score}, Maps: {map_count} total, {maps_with_scores} with scores")
    
    # Get map details
    cur.execute("""
        SELECT game_id, map, team_a_score, team_b_score
        FROM Maps
        WHERE match_id = ?
        ORDER BY game_id
    """, (match_id,))
    
    for map_row in cur.fetchall():
        gid, map_name, ta, tb = map_row
        print(f"    Map {gid} ({map_name}): {ta}-{tb}")
    print()

conn.close()
