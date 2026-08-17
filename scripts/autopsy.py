"""Trading Autopsy CLI (T103, D026).

Runs the full deterministic autopsy battery over trade confirmations (PDFs / TXT in private/)
or recorded transactions in the KUBERA database.

Usage:
  python scripts/autopsy.py                    # Auto-detects DB or private/statements
  python scripts/autopsy.py --dir private/statements
  python scripts/autopsy.py --days 90
  python scripts/autopsy.py --json
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

from analysis.autopsy import analyze_autopsy  # noqa: E402
from data.db import make_engine, make_session_factory  # noqa: E402
from data.models import Transaction  # noqa: E402
from data.statements import parse_directory  # noqa: E402
from settings import get_settings  # noqa: E402


def format_autopsy_terminal(report) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append("                 KUBERA TRADING AUTOPSY REPORT (T103, D026)")
    lines.append("=" * 72)
    lines.append("")

    # 1. Volume & Instruments
    p = report.instrument_profile
    lines.append("1. INSTRUMENT & VOLUME PROFILE")
    lines.append("-" * 72)
    lines.append(f"  Total Fills Executed   : {p.total_fills}")
    lines.append(f"  Total Economic Notional: ${p.total_notional:,.2f}")
    lines.append(
        f"  Option Fills           : {p.option_fills} ({p.option_pct:.1%}) "
        f"[${p.option_notional:,.2f} notional]"
    )
    lines.append(
        f"  Equity Fills           : {p.equity_fills} ({1 - p.option_pct:.1%}) "
        f"[${p.equity_notional:,.2f} notional]"
    )
    if p.option_fills > 0:
        if p.dte0_pct_of_options is not None:
            dte0_str = f"{p.dte0_fills} ({p.dte0_pct_of_options:.1%})"
        else:
            dte0_str = "0"
        lines.append(f"  0DTE Option Fills      : {dte0_str} of options")
        lines.append(f"  Option Rights          : {p.calls_count} Calls / {p.puts_count} Puts")
    lines.append("")

    # 2. Performance
    perf = report.performance
    lines.append("2. FIFO ROUND-TRIP PERFORMANCE & P&L")
    lines.append("-" * 72)
    lines.append(f"  Closed Round Trips     : {perf.round_trips}")
    lines.append(f"  Total Realized P&L     : ${perf.total_realized_pnl:,.2f}")
    if perf.round_trips > 0:
        wr_str = f"{perf.win_rate:.1%}" if perf.win_rate is not None else "N/A"
        pf_str = f"{perf.profit_factor:.2f}" if perf.profit_factor is not None else "N/A"
        po_str = f"{perf.payoff_ratio:.2f}" if perf.payoff_ratio is not None else "N/A"
        lines.append(
            f"  Win Rate               : {wr_str} "
            f"({perf.wins}W / {perf.losses}L / {perf.scratches}S)"
        )
        lines.append(f"  Profit Factor          : {pf_str}")
        lines.append(
            f"  Avg Win / Avg Loss     : ${perf.avg_win or 0:,.2f} / "
            f"${perf.avg_loss or 0:,.2f} (Payoff: {po_str})"
        )
        lines.append(
            f"  Largest Win / Loss     : ${perf.largest_win or 0:,.2f} / "
            f"${perf.largest_loss or 0:,.2f}"
        )
        lines.append(f"  Option Realized P&L    : ${perf.option_realized_pnl:,.2f}")
        lines.append(f"  Equity Realized P&L    : ${perf.equity_realized_pnl:,.2f}")
    else:
        lines.append("  (No closed round trips in this fill sample)")
    lines.append("")

    # 3. Holding Periods
    hp = report.holding_periods
    lines.append("3. HOLDING PERIOD DISTRIBUTION (T091b)")
    lines.append("-" * 72)
    if hp.get("all_same_day_unrecorded"):
        cnt = hp.get("same_day_unrecorded_count", 0)
        lines.append(
            f"  Same-Day Duration      : {cnt} trades (intraday times unrecorded on confirmations)"
        )
    elif hp.get("has_unrecorded_intraday_times"):
        cnt = hp.get("same_day_unrecorded_count", 0)
        lines.append(
            f"  Intraday Times         : {cnt} same-day trades have unrecorded intraday times"
        )
        if hp.get("median_days") is not None:
            lines.append(f"  Multi-Day Median Hold  : {hp['median_days']:.1f} days")
    elif hp.get("median_days") is not None:
        med = hp["median_days"]
        med_str = f"{med * 24.0:.1f} hours ({med:.3f} days)" if med < 1.0 else f"{med:.1f} days"
        lines.append(f"  Median Holding Time    : {med_str}")
    lines.append("  Bucket Distribution    :")
    lines.append("    Bucket        Count   Wins   Win Rate   Realized P&L")
    lines.append("    ------------  -----   ----   --------   ------------")
    for b_name, slot in hp.get("by_bucket", {}).items():
        if slot["round_trips"] > 0:
            wr = f"{slot['win_rate']:.1%}" if slot.get("win_rate") is not None else "   -"
            lines.append(
                f"    {b_name:<12}  {slot['round_trips']:>5}   {slot['wins']:>4}   "
                f"{wr:>8}   ${slot['realized_pnl']:>11,.2f}"
            )
    lines.append("")

    # 4. Behavioral Tells
    b = report.behavior
    lines.append("4. BEHAVIORAL TELLS & DISCIPLINE (T069 — computed within asset class)")
    lines.append("-" * 72)
    lines.append(f"  Options Sizing Drift   : {b.options.sizing_drift_verdict}")
    lines.append(f"  Options Post-Loss Pace : {b.options.post_loss_pace_verdict}")
    lines.append(f"  Equities Sizing Drift  : {b.equities.sizing_drift_verdict}")
    lines.append(f"  Equities Post-Loss Pace: {b.equities.post_loss_pace_verdict}")
    lines.append("")

    # 5. Symbols Breakdown
    lines.append("5. TOP SYMBOLS TRADED")
    lines.append("-" * 72)
    lines.append("  Symbol   Fills   Opt/Eq   0DTE   Notional       Realized P&L   Win Rate")
    lines.append("  ------   -----   ------   ----   ------------   ------------   --------")
    for s in report.symbols[:10]:
        wr = f"{s['win_rate']:.1%}" if s.get("win_rate") is not None else "   -"
        lines.append(
            f"  {s['symbol']:<6}   {s['fills']:>5}   "
            f"{s['option_fills']:>2}/{s['equity_fills']:<2}   "
            f"{s['dte0_fills']:>4}   "
            f"${s['total_notional']:>11,.2f}   "
            f"${s['realized_pnl']:>11,.2f}   "
            f"{wr:>8}"
        )
    lines.append("")

    # 6. Factual Narrative
    lines.append("6. NARRATIVE FINDINGS")
    lines.append("-" * 72)
    for n in report.narrative:
        lines.append(f"  * {n}")
    lines.append("")
    lines.append("=" * 72)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="KUBERA Trading Autopsy (T103, D026)")
    parser.add_argument("--dir", help="Directory of trade confirmation files (PDF/TXT)")
    parser.add_argument("--days", type=int, help="Limit to last N days")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    fills = []

    # If --dir specified or private/statements exists
    target_dir = Path(args.dir) if args.dir else (ROOT / "private" / "statements")
    if target_dir.exists() and any(target_dir.iterdir()):
        rep = parse_directory(target_dir)
        fills = rep.fills

    # Fallback to DB
    if not fills:
        s = get_settings()
        engine = make_engine(s.database_url)
        factory = make_session_factory(engine)
        with factory() as session:
            q = select(Transaction).order_by(Transaction.occurred_at)
            fills = list(session.execute(q).scalars().all())

    # Fallback to test fixtures if no files/DB found
    if not fills:
        fixture_dir = BACKEND / "tests" / "fixtures" / "schwab"
        if fixture_dir.exists():
            rep = parse_directory(fixture_dir)
            fills = rep.fills

    report = analyze_autopsy(fills)

    if args.json:
        out = {
            "total_fills": report.total_fills,
            "instrument_profile": report.instrument_profile.__dict__,
            "performance": report.performance.__dict__,
            "holding_periods": report.holding_periods,
            "behavior": report.behavior.__dict__,
            "day_of_week_distribution": report.day_of_week_distribution,
            "symbols": report.symbols,
            "narrative": report.narrative,
            "caveats": report.caveats,
            "note": report.note,
        }
        print(json.dumps(out, indent=2, default=str))
    else:
        print(format_autopsy_terminal(report))


if __name__ == "__main__":
    main()
