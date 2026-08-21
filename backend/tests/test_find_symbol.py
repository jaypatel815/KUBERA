"""T141 — find_symbol: the universe resolver. The owner's direction was
"KUBERA should have knowledge of every symbol in the market" — the data
tools were already universal; this closes the RESOLUTION gap (I007 class:
tickers guessed from LLM memory). Deterministic lookups over a fake SEC
directory; the ETF/trust miss path proven both ways."""

from types import SimpleNamespace

import pytest

from api.tools import ToolContext, ToolError, registry

DIRECTORY = [
    ("AAPL", "Apple Inc.", 320193),
    ("PLTR", "Palantir Technologies Inc.", 1321655),
    ("APP", "Applovin Corp.", 1751008),
    ("APLE", "Apple Hospitality REIT, Inc.", 1418121),
    ("BRK-B", "Berkshire Hathaway Inc.", 1067983),
]


class FakeEdgar:
    def ticker_directory(self):
        return list(DIRECTORY)


class FakeMarket:
    def __init__(self, price=None, exc=None):
        self._price, self._exc = price, exc

    def get_latest_trade(self, symbol):
        if self._exc:
            raise self._exc
        return SimpleNamespace(price=self._price)


def _run(query, market=None):
    return registry.execute("find_symbol", {"query": query},
                            ToolContext(edgar=FakeEdgar(), market=market))


def test_exact_ticker_wins_first():
    out = _run("pltr")
    assert out["exact_ticker_match"] is True
    assert out["matches"][0] == {"symbol": "PLTR",
                                 "name": "Palantir Technologies Inc.",
                                 "cik": 1321655}


def test_company_name_resolves_deterministically():
    out = _run("Palantir")
    assert out["matches"][0]["symbol"] == "PLTR"
    assert "never a guess" in out["note"]


def test_ambiguity_returns_candidates_not_a_silent_pick():
    out = _run("apple")
    symbols = [m["symbol"] for m in out["matches"]]
    # both Apples surface; exact-prefix name match ranks Apple Inc. first
    assert symbols[0] == "AAPL" and "APLE" in symbols
    assert "ASK the user" in out["note"]


def test_ticker_shaped_miss_probes_the_market_labeled():
    out = _run("SPY", market=FakeMarket(price=316.74))
    assert out["exact_ticker_match"] is False
    assert out["matches"][0]["symbol"] == "SPY"
    assert out["matches"][0]["cik"] is None
    assert "likely an ETF/trust" in out["tradable_note"]


def test_ticker_shaped_miss_with_dead_market_stays_unresolved():
    import httpx
    out = _run("ZZZZ", market=FakeMarket(exc=httpx.ConnectError("down")))
    assert out["matches"] == []
    assert "do not assume it exists" in out["tradable_note"]
    out2 = _run("ZZZZ", market=None)
    assert "no market client" in out2["tradable_note"]


def test_name_miss_is_empty_not_probed():
    # a NAME-shaped miss (too long for a ticker) gets no market probe —
    # probing "Standard Oil of Ohio" as a ticker would be nonsense
    out = _run("Standard Oil of Ohio")
    assert out["matches"] == [] and out["tradable_note"] is None


def test_missing_edgar_is_a_named_refusal():
    with pytest.raises(ToolError, match="EDGAR_CONTACT"):
        registry.execute("find_symbol", {"query": "AAPL"},
                         ToolContext(edgar=None))
