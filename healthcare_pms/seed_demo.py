"""Create a reproducible SQLite sample database in pending-change state."""
import argparse
from pathlib import Path
from database import DEFAULT_DB, initialize


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db",default=str(DEFAULT_DB),help="Database path (default: beside app.py)")
    parser.add_argument("--reset",action="store_true",help="Replace the selected database with clean sample data")
    args=parser.parse_args()
    path=Path(args.db)
    if path.exists() and not args.reset:
        parser.error(f"{path} already exists. Use --reset only if you want to replace it.")
    conn=initialize(path,reset=args.reset)
    print(f"Sample project database ready: {path.resolve()}")
    print("Initial change state: CR-001 Pending; baseline remains PKR 5,000,000 and 16 weeks.")
    conn.close()


if __name__=="__main__":
    main()
