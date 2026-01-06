import sys

def main():
    sys.stderr.write(
        "This utility is deprecated and archived in loadDB/_legacy/team_cleanup.py.\n"
        "Use JSON aliases in loadDB/aliases.json and rerun Elo/ingest.\n"
    )
    raise SystemExit(1)

if __name__ == "__main__":
    main()
