"""T119 (thesis view) + T121b (finnhub news merge) — composed, never invented."""

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from test_paper_loop import db  # noqa: F401

from api.tools import ToolContext, registry
from data.journal import record_decision
from data.watchlist import add_symbol


def _bars(n=250):
    d0 = date(2025, 6, 2)
    return SimpleNamespace(
        bars=[SimpleNamespace(close=100.0 + 0.1 * i, high=101.0 + 0.1 * i,
                              low=99.0 + 0.1 * i, volume=1000,
                              date=(d0 + timedelta(days=i)).isoformat())
              for i in range(n)],
        asof=datetime(2026, 8, 20, tzinfo=timezone.utc), source="fake")


# ------------------------------------------------------------ T119


def test_thesis_view_composes_owner_record(db):  # noqa: F811
    add_symbol(db, "SPY", note="core index position; add on 5% dips")
    record_decision(db, symbol="SPY", verdict="hold", confidence=0.6,
                    thesis="uptrend intact, holding", stop_price=95.0)

    market = SimpleNamespace(get_daily_bars=lambda s, days: _bars())
    out = registry.execute("get_thesis_view", {"symbol": "spy"},
                           ToolContext(db=db, market=market))
    assert out["symbol"] == "SPY"
    # the owner's words, verbatim — composed, not rewritten
    assert out["watchlist_thesis"]["note"] == \
        "core index position; add on 5% dips"
    assert out["watchlist_note_absent"] is None
    assert out["journal"][0]["thesis"] == "uptrend intact, holding"
    assert out["journal"][0]["invalidation_then"] == 95.0
    # the CURRENT plan carries its lens (I033 discipline)
    assert "weeks-to-months lens" in out["current_plan"]["regime"]
    assert out["current_plan"]["invalidation_level"] is not None
    # no fmp/fred in ctx -> catalysts hold only what exists (FOMC table
    # needs no key and may contribute scheduled entries)
    assert all(c["kind"] in ("earnings", "scheduled") for c in out["catalysts"])
    assert "composed not invented" in out["note"]


def test_thesis_view_names_absences(db):  # noqa: F811
    market = SimpleNamespace(get_daily_bars=lambda s, days: _bars())
    out = registry.execute("get_thesis_view", {"symbol": "NVDA"},
                           ToolContext(db=db, market=market))
    assert out["watchlist_thesis"] is None
    assert "not on the watchlist" in out["watchlist_note_absent"]
    assert out["journal"] == []
    assert "no journaled decisions" in out["journal_absent"]


# ------------------------------------------------------------ T121b


class _AlpacaNewsMarket:
    def get_news(self, symbols, limit):
        from data.market_data import NewsDigest
        from data.market_data import NewsItem as _NI
        return NewsDigest(
            symbols=symbols or [],
            items=[_NI(
                headline="Alpaca headline", summary="s", source="benzinga",
                url="https://news/1",
                published_ts=datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc),
                age_human="2h ago", symbols=["SPY"])],
            asof=datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc))


class _Finnhub:
    def company_news(self, symbol, days):
        return SimpleNamespace(items=[
            SimpleNamespace(headline="Finnhub fresh", news_source="wire",
                            url="https://news/2",
                            published_utc=datetime(2026, 8, 20, 11, 0,
                                                   tzinfo=timezone.utc)),
            SimpleNamespace(headline="Duplicate of alpaca", news_source="wire",
                            url="https://news/1",     # SAME url -> deduped
                            published_utc=datetime(2026, 8, 20, 9, 0,
                                                   tzinfo=timezone.utc)),
        ])


def test_news_merges_labels_and_dedupes_by_url():
    out = registry.execute(
        "get_news", {"symbols": "SPY", "limit": 8},
        ToolContext(market=_AlpacaNewsMarket(), finnhub=_Finnhub()))
    urls = [i["url"] for i in out["items"]]
    assert urls == ["https://news/2", "https://news/1"]   # newest first, deduped
    feeds = {i["url"]: i["feed"] for i in out["items"]}
    assert feeds["https://news/1"] == "alpaca-news"
    assert feeds["https://news/2"] == "finnhub"
    assert "added 1 item" in out["finnhub_note"]
    assert out["source"] == "alpaca-news + finnhub"


def test_news_without_finnhub_or_symbols_names_it():
    out = registry.execute("get_news", {"symbols": "SPY"},
                           ToolContext(market=_AlpacaNewsMarket()))
    assert "not configured" in out["finnhub_note"]
    assert all(i["feed"] == "alpaca-news" for i in out["items"])

    out2 = registry.execute("get_news", {},
                            ToolContext(market=_AlpacaNewsMarket(),
                                        finnhub=_Finnhub()))
    assert "market-wide" in out2["finnhub_note"]          # finnhub skipped
