import re
from loadDB.db_utils import get_conn


def clean_map_name(name: str | None) -> str:
    if not name:
        return 'Unknown'
    cleaned = name
    cleaned = re.sub(r"^\d+\s*-?\s*", "", cleaned)
    cleaned = re.sub(r"\s*\(pick\)\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"pick", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*\d{1,2}:\d{2}\s*(AM|PM)?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r":\d+$", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    return cleaned or 'Unknown'


def main():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, map FROM Maps")
    rows = cur.fetchall()
    updates = []
    for mid, name in rows:
        new_name = clean_map_name(name)
        if new_name != (name or ''):
            updates.append((new_name, mid))
    if not updates:
        print("No map title changes needed.")
        return
    cur.executemany("UPDATE Maps SET map = ? WHERE id = ?", updates)
    conn.commit()
    print(f"Updated {len(updates)} map titles.")


if __name__ == "__main__":
    main()
