"""T122c — the Kronos adapter: bridges NeoQuasar/Kronos-base to the runner.

Executed ONLY via kronos_run.py's --model-file seam, inside the T110b
boundary, with --python pointing at the model venv. This file is committed
as the reviewed reference; it contains NO machine paths — the Kronos repo
location arrives per-call:

    py scripts\\kronos_run.py forecast --model-file scripts\\kronos_adapter.py
        --python C:\\path\\to\\kronos-venv\\Scripts\\python.exe
        --model-config kronos_repo=C:\\path\\to\\Kronos

Written against the repo's DOCUMENTED API (README fetched 2026-08-20):
KronosTokenizer/Kronos.from_pretrained + KronosPredictor(model, tokenizer,
max_context=512).predict(df[OHLCV], x_timestamp, y_timestamp, pred_len,
T, top_p, sample_count). `sample_count` AVERAGES paths, which would
destroy the distribution — so this adapter draws N_PATHS independent
samples itself and builds the percentiles empirically. The distribution
IS the deliverable (D035); an averaged point would be exactly the thing
the pre-registration refuses to produce.

Before the first real forecast, run the shape check ONCE:

    py scripts\\kronos_shape_check.py
        --python C:\\path\\to\\kronos-venv\\Scripts\\python.exe
        --model-config kronos_repo=C:\\path\\to\\Kronos

Keep this file small enough to READ before running it — that is the
recorded T122b objection: the adapter executes with the model venv's full
site-packages, so its reviewability is the control.
"""

N_PATHS = 30          # independent sampled paths -> empirical percentiles
LOOKBACK = 400        # sessions of context (max_context is 512)
TEMPERATURE = 1.0     # documented default; NOT tuned per-run (pre-registered)
TOP_P = 0.9           # documented default; same


def forecast(payload: dict) -> dict:
    """kronos_run.py contract: payload in, four floats out. Any exception
    propagates — the boundary names it and the attempt records a failure."""
    import sys

    repo = (payload.get("config") or {}).get("kronos_repo")
    if not repo:
        raise ValueError(
            "config.kronos_repo missing — pass "
            "--model-config kronos_repo=<path to the cloned Kronos repo>")
    sys.path.insert(0, repo)

    # pandas lives in the owner's MODEL venv (Kronos requirements), not in
    # KUBERA's root venv — same narrow suppression rationale as `model`
    # below (I023 rule; Gemini's T122c review caught this one: the sandbox
    # had pandas ambiently, a clean venv does not — I036).
    import pandas as pd  # pyrefly: ignore

    # `model` is the Kronos REPO's package, present only in the owner's
    # model venv via the sys.path.insert above — invisible to this repo's
    # type checker by design (narrowest possible suppression, I023 rule).
    from model import Kronos, KronosPredictor, KronosTokenizer  # pyrefly: ignore

    ohlcv = payload.get("ohlcv") or {}
    for col in ("open", "high", "low", "close"):
        if not ohlcv.get(col):
            raise ValueError(f"payload.ohlcv.{col} missing — the runner "
                             "must send full bars")
    n = len(ohlcv["close"])
    lo = max(0, n - LOOKBACK)
    x_df = pd.DataFrame({
        "open": ohlcv["open"][lo:], "high": ohlcv["high"][lo:],
        "low": ohlcv["low"][lo:], "close": ohlcv["close"][lo:],
        "volume": (ohlcv.get("volume") or [0.0] * n)[lo:],
    })
    x_ts = pd.Series(pd.to_datetime(payload["dates"][lo:]))
    # the next session's timestamp: the target date the runner supplied
    # (weekends/holidays already handled upstream by real bar dates)
    y_ts = pd.Series(pd.to_datetime([payload["forecast_date"]]))

    tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
    model = Kronos.from_pretrained("NeoQuasar/Kronos-base")
    predictor = KronosPredictor(model, tokenizer, max_context=512)

    basis = float(ohlcv["close"][-1])
    sampled: list[float] = []
    for _ in range(N_PATHS):
        pred = predictor.predict(df=x_df, x_timestamp=x_ts, y_timestamp=y_ts,
                                 pred_len=1, T=TEMPERATURE, top_p=TOP_P,
                                 sample_count=1)
        sampled.append(float(pred["close"].iloc[0]) / basis - 1.0)

    sampled.sort()

    def pct(q: float) -> float:
        # nearest-rank on the sorted sample — simple, monotone, honest
        idx = min(len(sampled) - 1, max(0, round(q * (len(sampled) - 1))))
        return sampled[idx]

    return {
        "p05_frac": pct(0.05),
        "p50_frac": pct(0.50),
        "p95_frac": pct(0.95),
        "up_odds": sum(1 for r in sampled if r > 0.0) / len(sampled),
    }
