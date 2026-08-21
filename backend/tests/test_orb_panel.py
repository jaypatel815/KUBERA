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
    # opening the panel loads all three; the 60s poll refreshes all three
    assert "{ loadPortfolio(); loadMonitor(); loadBench(true); }" in text
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
