import sys

def main():
    sys.stderr.write(
        "This utility is deprecated and archived in loadDB/_legacy/map_cleanup.py.\n"
        "Use loadDB/cli and keep Maps normalized via ingest.\n"
    )
    raise SystemExit(1)

if __name__ == "__main__":
    main()
