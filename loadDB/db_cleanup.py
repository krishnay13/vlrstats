import sqlite3
import os
import argparse

ALLOWED_TABLES = {
    'Matches',
    'Maps',
    'Player_Stats',
    'Elo_History',
    'Elo_Current',
    'Player_Elo_History',
    'Player_Elo_Current',
}

INTERNAL_TABLES = {
    'sqlite_sequence',
}

def list_tables(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [r[0] for r in cur.fetchall()]


def cleanup_db(db_path: str, apply: bool = True):
    if not os.path.exists(db_path):
        raise SystemExit(f"DB not found at {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    tables = list_tables(conn)
    to_drop = [t for t in tables if t not in ALLOWED_TABLES and t not in INTERNAL_TABLES]

    print("Found tables:")
    for t in tables:
        print(f" - {t}")

    if not to_drop:
        print("No extraneous tables to drop.")
    else:
        print("Tables to drop:")
        for t in to_drop:
            print(f" - {t}")
        if apply:
            for t in to_drop:
                cur.execute(f"DROP TABLE IF EXISTS {t}")
            # Optional: remove orphaned indexes/triggers
            cur.execute("VACUUM")
            conn.commit()
            print("Dropped extraneous tables and vacuumed DB.")
        else:
            print("Dry-run: no changes applied.")

    conn.close()


def main():
    base_dir = os.path.dirname(__file__)
    db_path = os.path.abspath(os.path.join(base_dir, '..', 'valorant_esports.db'))
    parser = argparse.ArgumentParser(description="Clean up unused tables in the SQLite database")
    parser.add_argument('--db', type=str, default=db_path, help='Path to the SQLite DB file')
    parser.add_argument('--dry-run', action='store_true', help='Only show what would be dropped')
    args = parser.parse_args()
    cleanup_db(args.db, apply=not args.dry_run)

if __name__ == '__main__':
    main()
