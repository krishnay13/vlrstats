"""
One-off cleaner for obviously bad map-level scores in the Maps table.

We currently have rows where:
  - map names contain scraped duration strings like "SunsetPICK1:00:41"
  - team_a_score / team_b_score are tiny values like 1–0, 1–1, 1–3, etc.

Those are not valid Valorant map scores and come from a scraper parsing issue.
Until the scraper is fully corrected, this script:
  - normalizes the map name (strip trailing "PICK<time>" or "<time>" fragments)
  - sets team_a_score / team_b_score to NULL so the frontend treats them as missing
"""

import re

from .db_utils import get_conn


BAD_TOTALS = {1, 4}


def _clean_map_name(raw: str) -> str:
  """Strip duration / 'PICK' noise from map name."""
  if not raw:
    return raw

  name = raw

  # First, split off any 'PICK' suffix (e.g. 'SunsetPICK1:00:41')
  if "PICK" in name:
    name = name.split("PICK", 1)[0]

  # Then strip trailing time-like patterns (e.g. 'Icebox1:00:12' -> 'Icebox')
  name = re.sub(r"\d+:\d{2}:\d{2}$", "", name)
  name = re.sub(r"\d+:\d{2}$", "", name)

  return name.strip()


def fix_bad_map_scores() -> None:
  conn = get_conn()
  cur = conn.cursor()

  # Find maps with obviously impossible scores
  cur.execute(
    """
    SELECT id, map, team_a_score, team_b_score
    FROM Maps
    WHERE team_a_score IS NOT NULL
      AND team_b_score IS NOT NULL
      AND (
        (team_a_score = 1 AND team_b_score = 1)
        OR (team_a_score + team_b_score IN (1, 4))
      )
    """
  )
  rows = cur.fetchall()
  print(f"Found {len(rows)} Maps rows with impossible scores.")

  updated = 0
  for map_id, raw_map, a_score, b_score in rows:
    clean_name = _clean_map_name(raw_map)
    cur.execute(
      "UPDATE Maps SET map = ?, team_a_score = NULL, team_b_score = NULL WHERE id = ?",
      (clean_name, map_id),
    )
    updated += 1

  conn.commit()
  conn.close()
  print(f"Updated {updated} Maps rows (cleaned name + nulled scores).")


def main():
  fix_bad_map_scores()


if __name__ == "__main__":
  main()

