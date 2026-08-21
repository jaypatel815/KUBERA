"""T087 (Orb half) — wiring pins for the monitor panel. The payload's SHAPE
is tested in test_monitor_service; this pins that the Orb actually consumes
it: the fetch, the container, the poll, and the advisory footer can't be
silently dropped by a future orb.html rewrite. (JS behavior itself is
field-tested by the owner — there is no JS test rig in this repo, and these
greps are deliberately the cheapest guard that still guards.)"""

from pathlib import Path

ORB = Path(__file__).resolve().parents[2] / "apps" / "web" / "orb.html"


def test_monitor_panel_is_wired():
    text = ORB.read_text(encoding="utf-8")
    assert 'fetch("/api/monitor")' in text
    assert 'id="mon-body"' in text and 'id="mon-foot"' in text
    assert "loadMonitor()" in text
    # T157c: the dashboard is always open — everything loads at init and the
    # 60s poll refreshes it all (bench self-throttles inside loadBench)
    assert ("loadPortfolio(); loadMonitor(); loadBench(true); "
            "loadRisk(); loadHousehold();") in text
    assert "loadBench(false)" in text  # poll path (self-throttled to 10 min)
    # the no-positions answer and the days lens field are rendered
    assert "nothing to monitor" in text
    assert "days_lens" in text and "blind_spots" in text


def test_monitor_panel_escapes_untrusted_text():
    # every payload string goes through esc() — API text is data, not HTML
    text = ORB.read_text(encoding="utf-8")
    assert "function esc(" in text
    for field in ("p.days_lens", "p.structure", "a.detail", "p.symbol"):
        assert f"esc({field})" in text


def test_alert_notifications_are_wired():
    """T147 — the bell: local OS notifications on NEW alert transitions."""
    text = ORB.read_text(encoding="utf-8")
    assert 'id="btn-notify"' in text
    assert "Notification.requestPermission()" in text  # permission on gesture
    assert "notifyAlertTransitions" in text
    # transitions tracked every poll (enabling never bursts), alerts only
    assert 'a.severity === "alert"' in text
    assert "seenAlertKeys = new Set(current.map(c => c.key))" in text
    # the honest scope is stated where the user reads it
    assert "only while this panel is open (no push server)" in text


def test_dashboard_shell_and_household_card_are_wired():
    """T157c — the trading-desk layout: KPI row, cards, conversation dock,
    household card fed by /api/household. Every card carries its asof."""
    text = ORB.read_text(encoding="utf-8")
    for el in ('id="topbar"', 'id="kpis"', 'id="cards"', 'id="dock"',
               'id="kpi-tier"', 'id="kpi-dqs"', 'id="kpi-debt"',
               'id="kpi-excess"', 'id="house-body"'):
        assert el in text, f"missing {el}"
    assert 'fetch("/api/risk")' in text
    assert 'fetch("/api/household")' in text
    # manual-data honesty rendered in the owner's own frame (D039)
    assert "as you told me on" in text
    # the empty state teaches the chat path instead of showing a blank card
    assert "add my Visa" in text
    # household strings are escaped like every other API payload
    assert "esc(x.name)" in text and "esc(x.balance_asof)" in text
    # the voice loop survived the re-layout (the dock keeps the orb alive)
    assert 'id="orb"' in text and 'id="typed"' in text


def test_benchmark_panel_is_wired():
    """T143 — performance vs SPY: /api/benchmark drawn inline, no chart lib."""
    text = ORB.read_text(encoding="utf-8")
    assert 'fetch("/api/benchmark?days=90")' in text
    assert 'id="bench-chart"' in text and 'id="bench-foot"' in text
    assert "portfolio_norm" in text and "benchmark_norm" in text
    assert "excess" in text  # the honest number is displayed, not just curves
    # degradations are NAMED, never blank
    assert "run scripts/sync.py daily" in text
    assert "benchmark unavailable" in text
    # API detail text is escaped before it touches innerHTML
    assert "esc(detail)" in text
    # no chart library crept in — the Orb stays a single self-contained file
    assert "cdn" not in text.lower()
    assert "chart.js" not in text.lower()
