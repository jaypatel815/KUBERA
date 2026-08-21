"""T136 — the PWA shell: Phase 5 begins per D004 (PWA, not the spec's
Flutter line — that tension is recorded in the ticket). What matters most
here is the DOCTRINE pin: the service worker may cache the shell, and it
may NEVER cache money — a cached /portfolio is stale data presented as
current, AGENTS.md priority 1."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)
WEB = Path(__file__).resolve().parents[2] / "apps" / "web"


def test_pwa_assets_served_with_correct_types():
    r = client.get("/manifest.webmanifest")
    assert r.status_code == 200
    assert "application/manifest+json" in r.headers["content-type"]
    assert client.get("/sw.js").status_code == 200
    assert "image/svg+xml" in client.get("/icon.svg").headers["content-type"]


def test_manifest_is_installable_shaped():
    m = json.loads((WEB / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert m["name"] == "KUBERA" and m["display"] == "standalone"
    assert m["start_url"] == "/" and m["scope"] == "/"
    assert m["icons"] and m["icons"][0]["src"] == "/icon.svg"
    # the app's own honest description travels with the install
    assert "paper-only" in m["description"]


def test_orb_registers_the_worker_and_links_the_manifest():
    text = (WEB / "orb.html").read_text(encoding="utf-8")
    assert 'rel="manifest"' in text and "/manifest.webmanifest" in text
    assert 'serviceWorker" in navigator' in text
    assert 'register("/sw.js")' in text


def test_service_worker_never_caches_money():
    sw = (WEB / "sw.js").read_text(encoding="utf-8")
    # the API/network-only guard exists and returns BEFORE any cache logic
    assert '/api/' in sw and '"/portfolio"' in sw
    guard = sw.index('url.pathname.startsWith("/api/")')
    cache_logic = sw.index("caches.match")
    assert guard < cache_logic, "the money guard must run before any caching"
    # and the shell list contains only shell — no api, no portfolio
    shell_line = next(ln for ln in sw.splitlines() if ln.startswith("const SHELL ="))
    assert "/api" not in shell_line and "portfolio" not in shell_line


# ---- T157g: vendored fonts route ---------------------------------------------

def test_font_route_rejects_bad_names_and_hints_when_absent():
    from fastapi.testclient import TestClient

    from api.main import app
    c = TestClient(app)
    # traversal / wrong-shape names never touch the filesystem
    assert c.get("/fonts/..%2Forb.html").status_code == 404
    assert c.get("/fonts/evil.js").status_code == 404
    # a valid-shaped name that is not vendored yet -> the one-time command
    r = c.get("/fonts/rubik-700.woff2")
    if r.status_code == 404:                      # not yet fetched (CI, sandbox)
        assert "fetch_fonts" in r.text
    else:                                          # owner machine, post-fetch
        assert r.headers["content-type"].startswith("font/woff2")


def test_intraday_bars_route_shape():
    """T157h — the candle panel's raw-bars route exists and degrades named."""
    from fastapi.testclient import TestClient

    from api.main import app
    r = TestClient(app).get("/api/market/SPY/intraday-bars?timeframe=5Min&days=1")
    # sandbox/CI: feed unreachable -> 502 with the named network error;
    # owner machine: 200 with {symbol, timeframe, bars, asof, source}
    assert r.status_code in (200, 502)
    if r.status_code == 200:
        body = r.json()
        assert body["symbol"] == "SPY" and "bars" in body
