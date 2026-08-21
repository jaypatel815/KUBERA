"""T156 — import card CSV exports into spending_entries, idempotently.

Drop card exports into private/spending/ (gitignored), then:

    python scripts/import_spending.py                 # imports every CSV there
    python scripts/import_spending.py path\\to\\file.csv
    python scripts/import_spending.py --negate        # exports where CHARGES
                                                      # are negative numbers

Categories come from private/spending_rules.json (substring -> category,
created with starter rules on first run — edit it, then re-run; unmatched
merchants are listed in every report and land as "uncategorized", never
guessed). Re-importing a file, or an overlapping newer export, writes
nothing twice. Exit 0 = clean; 1 = a file was refused.
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from data.db import make_engine, make_session_factory  # noqa: E402
from data.spending_import import (  # noqa: E402
    SpendingImportError,
    import_csv,
    load_rules,
    write_starter_rules,
)

SPENDING_DIR = REPO_ROOT / "private" / "spending"
RULES_PATH = REPO_ROOT / "private" / "spending_rules.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csvs", nargs="*", type=Path,
                    help=f"CSV files (default: {SPENDING_DIR}/*.csv)")
    ap.add_argument("--rules", type=Path, default=RULES_PATH)
    ap.add_argument("--negate", action="store_true",
                    help="this export writes charges as NEGATIVE amounts")
    args = ap.parse_args()

    if not args.rules.exists():
        write_starter_rules(args.rules)
        print(f"created starter rule map at {args.rules} — edit it anytime")
    try:
        rules = load_rules(args.rules)
    except SpendingImportError as e:
        print(f"REFUSED: {e}")
        return 1

    files = args.csvs or sorted(SPENDING_DIR.glob("*.csv"))
    if not files:
        SPENDING_DIR.mkdir(parents=True, exist_ok=True)
        print(f"no CSVs found — drop card exports into {SPENDING_DIR}")
        return 0

    engine = make_engine()
    session_factory = make_session_factory(engine)
    failed = False
    with session_factory() as session:
        for f in files:
            try:
                report = import_csv(session, f, rules, negate=args.negate)
            except (SpendingImportError, OSError) as e:
                print(f"REFUSED {f}: {e}")
                failed = True
                continue
            print(report.summary())
    print("done — the dashboard's budget card and get_household now see "
          "these entries")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
