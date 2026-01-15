"""List problematic matches with their IDs and map scores - matches validation logic exactly."""
from .db_utils import get_conn

conn = get_conn()
cur = conn.cursor()

problems = []

# All match_ids in DB
cur.execute("SELECT match_id FROM Matches")
all_match_ids = [row[0] for row in cur.fetchall()]

for mid in all_match_ids:
    # Maps existence
    cur.execute("SELECT COUNT(*) FROM Maps WHERE match_id = ?", (mid,))
    map_count = cur.fetchone()[0] or 0

    # Get match scores
    cur.execute("SELECT team_a_score, team_b_score FROM Matches WHERE match_id = ?", (mid,))
    row = cur.fetchone()
    if not row:
        continue
    
    a_score, b_score = row
    a_score = a_score or 0
    b_score = b_score or 0

    # Check for draws
    if a_score == b_score and a_score > 0:
        problems.append((mid, 'draw', a_score, b_score))
        continue

    # Check for single map wins (EXCEPT showmatches which are BO1)
    max_score = max(a_score, b_score)
    if max_score > 0 and max_score < 2:
        # Check if this is a showmatch
        cur.execute("SELECT match_name, tournament, match_type FROM Matches WHERE match_id = ?", (mid,))
        match_info = cur.fetchone()
        if match_info:
            match_type = (match_info[2] or '').upper() if len(match_info) > 2 else ''
            is_showmatch = match_type == 'SHOWMATCH'
            if not is_showmatch:
                # Fallback: check match_name and tournament fields
                match_name = (match_info[0] or '').lower()
                tournament = (match_info[1] or '').lower()
                is_showmatch = 'showmatch' in match_name or 'showmatch' in tournament
            if not is_showmatch:
                problems.append((mid, 'single_map_win', a_score, b_score))
        else:
            problems.append((mid, 'single_map_win', a_score, b_score))
        continue

    # Compare against map wins if we have maps with scores
    if map_count > 0:
        cur.execute("""
            SELECT team_a_score, team_b_score
            FROM Maps
            WHERE match_id = ?
              AND team_a_score IS NOT NULL
              AND team_b_score IS NOT NULL
        """, (mid,))
        map_rows = cur.fetchall()
        if map_rows:
            # Check for impossible map-level scores
            bad_map_score = False
            for ta, tb in map_rows:
                ta = ta or 0
                tb = tb or 0
                total = ta + tb
                if total in (1, 4) or (ta == tb and ta > 0 and ta < 10):
                    bad_map_score = True
                    break

            if bad_map_score:
                problems.append((mid, 'bad_map_score', a_score, b_score))
            else:
                # Compare aggregate series score vs map wins
                a_wins = sum(1 for ta, tb in map_rows if (ta or 0) > (tb or 0))
                b_wins = sum(1 for ta, tb in map_rows if (tb or 0) > (ta or 0))
                if a_wins + b_wins >= 2:
                    if a_wins != a_score or b_wins != b_score:
                        problems.append((mid, 'mismatch', a_score, b_score, a_wins, b_wins))

print("=" * 100)
print(f"PROBLEMATIC MATCHES ({len(problems)} total)")
print("=" * 100)
print()

for problem in problems:
    match_id = problem[0]
    issue_type = problem[1]
    
    # Get match info
    cur.execute("SELECT team_a, team_b, team_a_score, team_b_score FROM Matches WHERE match_id = ?", (match_id,))
    match_info = cur.fetchone()
    if not match_info:
        continue
    
    team_a, team_b, a_score, b_score = match_info
    print(f"Match ID: {match_id}")
    print(f"  Teams: {team_a} vs {team_b}")
    print(f"  Match Score: {a_score}-{b_score}")
    print(f"  Issue: {issue_type}")
    
    if issue_type == 'mismatch':
        print(f"  Map Wins: {problem[4]}-{problem[5]} (mismatch!)")
    
    # Get map details
    cur.execute("""
        SELECT game_id, map, team_a_score, team_b_score
        FROM Maps
        WHERE match_id = ?
        ORDER BY game_id
    """, (match_id,))
    
    maps = cur.fetchall()
    print(f"  Maps ({len(maps)}):")
    for gid, map_name, ta, tb in maps:
        print(f"    Map {gid} ({map_name}): {ta}-{tb}")
    
    # Calculate map wins
    if maps:
        a_wins = sum(1 for _, _, ta, tb in maps if ta is not None and tb is not None and (ta or 0) > (tb or 0))
        b_wins = sum(1 for _, _, ta, tb in maps if ta is not None and tb is not None and (tb or 0) > (ta or 0))
        print(f"  Map Wins Calculated: {a_wins}-{b_wins}")
    
    print()

print("=" * 100)
print(f"Total problematic matches: {len(problems)}")
print("=" * 100)
print()
print("Match IDs:", sorted(set(p[0] for p in problems)))

conn.close()
