import sys


def setup_database():
    sys.stderr.write(
        "This DB initializer is deprecated.\n"
        "Archived original in loadDB/_legacy/init_db.py.\n"
        "Prefer loadDB/db_utils + loadDB/cli or reset_db_2025.py.\n"
    )
    raise SystemExit(1)


if __name__ == "__main__":
    setup_database()
