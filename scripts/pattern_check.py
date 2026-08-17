"""Pre-Trade Pattern Warnings CLI (T104, D026).

Evaluates a planned trade setup against your historical execution records
(from DB transactions or statement confirmations) to detect recurring behavioral
pitfalls (0DTE negative expectancy, revenge sizing drift after losses, post-loss
tilt tempo, symbol track record, day-of-week disadvantages).

Usage:
  python scripts/pattern_check.py SPY
  python scripts/pattern_check.py SPY --dte 0 --notional 5000
  python scripts/pattern_check.py SPY260315C00500000 --qty 10 --price 2.50
  python scripts/pattern_check.py AAPL --notional 15000 --action buy
  python scripts/pattern_check.py SPY --json
"""

import argparse
import json
import sys
from pathlib import Path

# Add backend directory to sys.path
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import select  # noqa: E402

from analysis.pattern_warning import ProposedTrade, evaluate_pattern_warnings  # noqa: E402
from data.db import make_engine, make_session_factory  # noqa: E402
from data.models import Transaction  # noqa: E402
from data.statements import parse_directory  # noqa: E402
from settings import get_settings  # noqa: E402


def format_pattern_terminal(rep) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append("           KUBERA PRE-TRADE PATTERN EVALUATION (T104, D026)")
    lines.append("=" * 72)
    lines.append("")

    # Proposed trade header
    lines.append(f"  Proposed Symbol  : {rep.symbol}")
    lines.append(f"  Underlying       : {rep.underlying}")
    lines.append(f"  Action           : {rep.proposed_action.upper()}")
    lines.append(f"  Asset Type       : {rep.asset_type.upper()}")
    if rep.proposed_notional is not None:
        lines.append(f"  Proposed Notional: ${rep.proposed_notional:,.2f}")
    if rep.is_0dte:
        lines.append("  Option Profile   : 0DTE (Expires Today)")
    lines.append(
        f"  Historical Base  : {rep.historical_trips_count} completed round trips evaluated"
    )
    lines.append("")

    # Verdict
    v_map = {
        "warning_triggered": "[!] WARNING: Setup matches historical behavioral/loss patterns",
        "caution": "[?] CAUTION: Notable historical performance characteristics detected",
        "clear": "[+] CLEAR: No historical negative-expectancy or revenge patterns triggered",
        "insufficient_history": (
            "[-] INSUFFICIENT DATA: Historical trade count below statistical minimum"
        ),
    }
    lines.append("-" * 72)
    lines.append(f"VERDICT: {v_map.get(rep.verdict, rep.verdict)}")
    lines.append("-" * 72)
    lines.append("")

    if rep.warnings:
        lines.append(f"IDENTIFIED PATTERNS ({rep.warnings_count}):")
        for i, w in enumerate(rep.warnings, 1):
            sev_tag = f"[{w.severity.upper()}]"
            lines.append(f"  {i}. {sev_tag} {w.headline}")
            lines.append(f"     Category   : {w.category}")
            lines.append(f"     Sample Size: N = {w.sample_size}")
            lines.append(f"     Details    : {w.narrative}")
            lines.append("")
    else:
        for n in rep.narrative:
            lines.append(f"  {n}")
        lines.append("")

    if rep.caveats:
        lines.append("CAVEATS & SAMPLE LIMITATIONS:")
        for c in rep.caveats:
            lines.append(f"  * {c}")
        lines.append("")

    lines.append("=" * 72)
    lines.append("NOTE: Descriptive historical analysis only (D026). Zero prediction.")
    lines.append("=" * 72)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="KUBERA Pre-Trade Pattern Warning Diagnostic")
    parser.add_argument("symbol", nargs="?", help="Symbol or OCC option symbol (e.g. SPY, AAPL)")
    parser.add_argument("--action", default="buy", help="Action: buy, sell, short, cover")
    parser.add_argument("--asset-type", default=None, choices=["equity", "option"])
    parser.add_argument("--qty", type=float, default=None, help="Proposed quantity")
    parser.add_argument("--price", type=float, default=None, help="Estimated / limit price")
    parser.add_argument(
        "--notional", type=float, default=None, help="Explicit proposed notional ($)"
    )
    parser.add_argument("--dte", type=int, default=None, help="Days to expiration (0 = 0DTE)")
    parser.add_argument("--dir", default=None, help="Path to statement files")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text report")

    args = parser.parse_args()

    if not args.symbol:
        parser.print_help()
        sys.exit(1)

    fills = []
    # 1. Check directory if specified
    if args.dir:
        p = Path(args.dir)
        if not p.exists():
            print(f"Error: Directory not found: {args.dir}", file=sys.stderr)
            sys.exit(1)
        parsed = parse_directory(p)
        fills = parsed.fills
    else:
        # 2. Query DB
        try:
            s = get_settings()
            engine = make_engine(s.database_url)
            session_factory = make_session_factory(engine)
            with session_factory() as session:
                q = select(Transaction).order_by(Transaction.occurred_at)
                fills = list(session.execute(q).scalars().all())
        except Exception:
            fills = []

        # 3. Fallback to private/statements if DB has no fills
        if not fills:
            p = ROOT / "private" / "statements"
            if p.exists():
                parsed = parse_directory(p)
                fills = parsed.fills

    proposed = ProposedTrade(
        symbol=args.symbol,
        action=args.action,
        asset_type=args.asset_type or "equity",
        qty=args.qty,
        price=args.price,
        notional=args.notional,
        dte=args.dte,
    )

    rep = evaluate_pattern_warnings(fills, proposed)

    if args.json:
        out = {
            "symbol": rep.symbol,
            "underlying": rep.underlying,
            "proposed_action": rep.proposed_action,
            "asset_type": rep.asset_type,
            "proposed_notional": rep.proposed_notional,
            "is_0dte": rep.is_0dte,
            "verdict": rep.verdict,
            "warnings_count": rep.warnings_count,
            "has_high_severity": rep.has_high_severity,
            "historical_trips_count": rep.historical_trips_count,
            "warnings": [
                {
                    "category": w.category,
                    "severity": w.severity,
                    "headline": w.headline,
                    "sample_size": w.sample_size,
                    "evidence": w.evidence,
                    "narrative": w.narrative,
                }
                for w in rep.warnings
            ],
            "narrative": rep.narrative,
            "caveats": rep.caveats,
            "asof": rep.asof.isoformat(),
            "note": rep.note,
        }
        print(json.dumps(out, indent=2))
    else:
        print(format_pattern_terminal(rep))


if __name__ == "__main__":
    main()
