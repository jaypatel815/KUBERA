"""T122c — the adapter shape check: run ONCE on the owner's machine before
`kronos_run.py start`. Sends the real adapter a tiny SYNTHETIC OHLCV series
(clearly test fixture, never logged anywhere) through the same T110b
boundary the campaign uses, and verifies the four keys come back ordered
and in range. A model whose first invocation happens mid-campaign is a
budget attempt wasted on plumbing.

    py scripts\\kronos_shape_check.py
        --python C:\\path\\to\\kronos-venv\\Scripts\\python.exe
        --model-config kronos_repo=C:\\path\\to\\Kronos

Exit 0 = adapter answers correctly (weights downloaded, imports work);
1 = named failure. Slow on first run: from_pretrained downloads ~400MB.
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from research.kronos_runner import RunnerError, call_model  # noqa: E402

ADAPTER = REPO_ROOT / "scripts" / "kronos_adapter.py"

# Synthetic fixture bars — 60 sessions of a gently rising series. This is
# TEST DATA by design (shape check, not a forecast); nothing here is ever
# logged to research_forecasts.
N = 60
DATES = [f"2026-{5 + i // 28:02d}-{(i % 28) + 1:02d}" for i in range(N)]
CLOSES = [100.0 + 0.3 * i for i in range(N)]
OHLCV = {
    "open": [c - 0.2 for c in CLOSES],
    "high": [c + 0.5 for c in CLOSES],
    "low": [c - 0.6 for c in CLOSES],
    "close": CLOSES,
    "volume": [1_000_000.0] * N,
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Prove the Kronos adapter answers before the campaign.")
    ap.add_argument("--python", required=True,
                    help="the model venv's interpreter")
    ap.add_argument("--model-config", action="append", default=[],
                    metavar="KEY=VALUE")
    ap.add_argument("--timeout", type=float, default=1800.0,
                    help="seconds (first run downloads ~400MB)")
    args = ap.parse_args(argv)

    cfg = {}
    for item in args.model_config:
        if "=" not in item:
            print(f"REFUSED: --model-config '{item}' is not KEY=VALUE")
            return 1
        k, v = item.split("=", 1)
        cfg[k.strip()] = v.strip()

    print("calling the adapter through the T110b boundary with a 60-bar "
          "synthetic series (first run downloads the weights; be patient)")
    try:
        out = call_model(ADAPTER.read_text(encoding="utf-8"), "forecast",
                         "SHAPECHECK", CLOSES, DATES, "2026-08-24",
                         python=args.python, timeout_s=args.timeout,
                         ohlcv=OHLCV, config=cfg)
    except RunnerError as e:
        print(f"SHAPE CHECK: FAIL — {e}")
        return 1
    print(f"SHAPE CHECK: PASS — p05 {out['p05_frac']:+.3%}, "
          f"p50 {out['p50_frac']:+.3%}, p95 {out['p95_frac']:+.3%}, "
          f"up-odds {out['up_odds']:.0%} (ordering and ranges already "
          "enforced by call_model). The campaign may start.")
    print("NOTE: these numbers are from SYNTHETIC bars — they mean nothing "
          "and are logged nowhere; only the shape was under test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
