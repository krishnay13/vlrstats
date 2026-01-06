import sys


# Set up the SQLite database
def setup_database():
    sys.stderr.write(
        "This DB initializer is deprecated.\n"
        "Archived original in loadDB/_legacy/db_init.py.\n"
        "Prefer loadDB/db_utils + loadDB/cli or reset_db_2025.py.\n"
    )
    raise SystemExit(1)


# Database insertion functions
def insert_match(*args, **kwargs):
    setup_database()


def insert_map(*args, **kwargs):
    setup_database()


def get_or_insert_team(*args, **kwargs):
    setup_database()


def get_or_insert_player(*args, **kwargs):
    setup_database()


def insert_player_stats(*args, **kwargs):
    setup_database()


if __name__ == "__main__":
    setup_database()
