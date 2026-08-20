"""T087c — the shared monitor service and its endpoint: one implementation,
two surfaces, proven with fakes (no network, no ambient .env dependence).

The CLI's composition tests stay in test_monitor.py (pure judge). Here:
run_monitor's assembly, run_payload's lens-labeled shape (incl. the I033
explainer), and GET /api/monitor via dependency overrides.
"""

from dataclasses import replace
from datetime import date, timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient

from analysis.monitor import MonitorAlert, PositionCheck, summarize
from api.main import app, get_alpaca_client, get_market_client
from api.monitor_service import (
    MonitorRun,
    PositionRead,
    run_monitor,
    run_payload,
)
from settings import KuberaSettings, get_settings

client = TestClient(app)


# --- fakes -----------------------------------------------------------------

def _daily_bars(n: int, start: float = 50.0, step: float = 0.5):
    """n rising daily bars — enough structure for the regime/levels/plan
    composition to run for real (the service is NOT mocked, only the I/O)."""
    d0 = date(2025, 9, 1)
    bars = []
    for i in range(n):
        c = start + step * i
        bars.append(SimpleNamespace(
            date=(d0 + timedelta(days=i)).isoformat(),
            open=c - 0.2, high=c + 0.4, low=c - 0.5, close=c,
            volume=1_000_000 + 1_000 * i,
        ))
    return SimpleNamespace(bars=bars, source="test-feed")


class FakeMarket:
    def __init__(self, n_days: int = 80):
        self._n = n_days

    def get_daily_bars(self, symbol, days=250):
        return _daily_bars(self._n)

    def get_latest_trade(self, symbol):
        return SimpleNamespace(price=89.5)

    def get_intraday_bars(self, symbol, timeframe="5Min", days=9):
        return SimpleNamespace(bars=[], source="test-feed")  # named blind spot


class FakeAlpaca:
    def __init__(self, positions):
        self._positions = positions

    def get_positions(self):
        return self._positions


class ExplodingMarket:
    def __getattr__(self, name):  # any use = the shortcut was not taken
        raise AssertionError("market must not be touched with no positions")


def _pos(symbol="SPY", qty=10.0, plpc=0.031):
    return SimpleNamespace(symbol=symbol, qty=qty, unrealized_plpc=plpc)


# --- run_monitor -----------------------------------------------------------

def test_run_monitor_composes_reads_and_summary():
    run = run_monitor(FakeAlpaca([_pos(), _pos("QQQ", 5, -0.012)]),
                      FakeMarket(), windows=["FOMC decision window"])
    assert [r.symbol for r in run.positions] == ["SPY", "QQQ"]
    assert run.summary.positions == 2
    r = run.positions[0]
    assert r.days_line  # D035: the days lens is always present
    assert r.check.regime is not None  # 80 bars = a real structural read
    assert r.check.week_change_frac is not None
    # the injected event window arrived as a watch on every position
    assert all(any(a.kind == "event_window" for a in p.check.alerts)
               for p in run.positions)
    # empty intraday bars became a NAMED blind spot, not a crash
    assert any("VWAP" in n for n in r.check.notes)
    assert run.asof_utc and run.calendar_note is None


def test_run_monitor_no_positions_never_touches_market():
    run = run_monitor(FakeAlpaca([]), ExplodingMarket())
    assert run.positions == [] and run.summary.positions == 0
    assert run.summary.exit_code == 0  # nothing held = nothing burning


def test_run_monitor_thin_history_degrades_by_name():
    run = run_monitor(FakeAlpaca([_pos()]), FakeMarket(n_days=10),
                      windows=[])
    c = run.positions[0].check
    assert c.regime is None            # 10 bars: no structural read
    assert c.notes                      # blind spots are NAMED
    assert run.positions[0].days_line  # the days lens still answers


# --- run_payload -----------------------------------------------------------

def _hand_run(check: PositionCheck, days_line="SPY days: example"):
    read = PositionRead(symbol=check.symbol, qty=10.0,
                        unrealized_plpc=0.05, days_line=days_line,
                        check=check)
    return MonitorRun("2026-08-20T14:00:00+00:00", [read],
                      summarize([check]), None)


def test_payload_carries_every_lens_and_the_i033_explainer():
    # the exact case from the owner's first live run: structural uptrend,
    # red week — the payload must say both AND explain the meeting point
    check = PositionCheck(symbol="SPY", price=316.74, regime="trending_up",
                          week_change_frac=-0.0158)
    p = run_payload(_hand_run(check))
    pos = p["positions"][0]
    assert pos["structure"].startswith("trending_up (daily structure")
    assert pos["week_change_frac"] == -0.0158
    assert "normal" in pos["context_note"]  # I033: said where lenses meet
    assert pos["quiet"] is True and pos["days_lens"]
    assert p["summary"]["needs_eyes_now"] is False
    assert p["advisory"].startswith("advisory only")
    assert p["asof_utc"]


def test_payload_alerts_flip_needs_eyes_and_context_note_stays_scoped():
    alert = MonitorAlert("SPY", "alert", "invalidation_hit", "through 300")
    check = PositionCheck(symbol="SPY", price=299.0, regime="range_bound",
                          alerts=[alert], week_change_frac=0.01)
    p = run_payload(_hand_run(replace(check)))
    pos = p["positions"][0]
    assert pos["context_note"] is None      # green week / no uptrend = no note
    assert pos["quiet"] is False
    assert pos["alerts"] == [{"severity": "alert", "kind": "invalidation_hit",
                              "detail": "through 300"}]
    assert p["summary"]["needs_eyes_now"] is True


# --- GET /api/monitor ------------------------------------------------------

def _override_clients(alpaca, market):
    app.dependency_overrides[get_alpaca_client] = lambda: alpaca
    app.dependency_overrides[get_market_client] = lambda: market
    # no FRED key -> the event-window fetch stays on the keyless FOMC table:
    # deterministic regardless of the machine's ambient .env, no network
    app.dependency_overrides[get_settings] = (
        lambda: KuberaSettings(_env_file=None)
    )


def test_endpoint_serves_the_same_implementation():
    _override_clients(FakeAlpaca([_pos()]), FakeMarket())
    try:
        r = client.get("/api/monitor")
        assert r.status_code == 200
        body = r.json()
        assert body["summary"]["positions"] == 1
        assert body["positions"][0]["symbol"] == "SPY"
        assert body["positions"][0]["days_lens"]
        assert "advisory" in body  # never places/cancels/resizes — in writing
    finally:
        app.dependency_overrides.clear()


def test_endpoint_names_broker_failure_as_502():
    from data.alpaca import AlpacaError

    class BrokenAlpaca:
        def get_positions(self):
            raise AlpacaError("alpaca GET /positions failed: 401")

    _override_clients(BrokenAlpaca(), FakeMarket())
    try:
        r = client.get("/api/monitor")
        assert r.status_code == 502
        assert "AlpacaError" in r.json()["detail"]
    finally:
        app.dependency_overrides.clear()
