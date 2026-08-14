"""I007–I010 defenses — symbol alignment, deflection detection, human-readable
ages, and portfolio auto-priming (all born from real owner transcripts)."""

import httpx
from test_alpaca import ACCOUNT_JSON, POSITIONS_JSON, paper_settings

from api.chat import _user_tickers, ensure_symbol_alignment
from data.alpaca import AlpacaClient
from data.market_data import human_age


def _alpaca_fake() -> AlpacaClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/v2/account" in request.url.path:
            return httpx.Response(200, json=ACCOUNT_JSON)
        return httpx.Response(200, json=POSITIONS_JSON)

    return AlpacaClient(settings=paper_settings(), transport=httpx.MockTransport(handler))


def test_portfolio_priming_puts_data_in_front_of_the_model():
    from api.chat import prime_portfolio
    from api.tools import ToolContext

    trail, asofs = [], {}
    with _alpaca_fake() as a:
        system = prime_portfolio(
            "BASE PROMPT", "can you check my portfolio for a positions on spy",
            ToolContext(alpaca=a), trail, asofs,
        )
    assert "AUTO-FETCHED PORTFOLIO" in system
    assert "Do NOT ask the user for share counts" in system
    assert trail == [{"name": "get_portfolio", "arguments": {"auto_primed": True}}]
    assert "get_portfolio" in asofs  # recency footer sees the primed fetch


def test_portfolio_priming_is_a_silent_noop_without_intent_or_broker():
    from api.chat import prime_portfolio
    from api.tools import ToolContext

    # no portfolio intent: untouched
    with _alpaca_fake() as a:
        assert prime_portfolio("BASE", "what regime is SPY in?",
                               ToolContext(alpaca=a), [], {}) == "BASE"
    # intent but no broker in context: untouched (never crashes the turn)
    assert prime_portfolio("BASE", "check my portfolio",
                           ToolContext(), [], {}) == "BASE"


def _trail(*symbols):
    return [{"name": "size_position", "arguments": {"symbol": s}} for s in symbols]


def test_the_spy_tsla_transcript_is_caught():
    reply = ensure_symbol_alignment(
        "TSLA Size-Position Result ...",
        "Should I buy and hold SPY today?",
        _trail("TSLA"),
    )
    assert "⚠ Symbol check" in reply
    assert "SPY" in reply and "TSLA" in reply
    assert "misdirected" in reply


def test_matching_symbols_stay_silent():
    reply = ensure_symbol_alignment("SPY looks...", "Should I buy SPY?", _trail("SPY"))
    assert "Symbol check" not in reply
    # any overlap is enough (multi-symbol questions)
    multi = ensure_symbol_alignment("...", "Compare SPY and QQQ",
                                    _trail("SPY", "AAPL"))
    assert "Symbol check" not in multi


def test_no_named_tickers_stays_silent():
    reply = ensure_symbol_alignment(
        "...", "how is my portfolio doing today?", _trail("SPY"))
    assert "Symbol check" not in reply
    # tool calls without symbols never trigger either
    assert "Symbol check" not in ensure_symbol_alignment(
        "...", "Should I buy SPY?", [{"name": "get_portfolio", "arguments": {}}])


def test_ticker_extraction():
    assert _user_tickers("Should I buy and hold SPY today?") == {"SPY"}
    assert _user_tickers("thoughts on $tsla?") == {"TSLA"}
    assert _user_tickers("is the ETF OK for MY IPS?") == set()  # all stopwords
    assert _user_tickers("compare SPY, QQQ and AAPL") == {"SPY", "QQQ", "AAPL"}


def test_the_hold_spy_deflection_transcript_is_caught():
    from api.chat import ensure_no_deflection

    reply = ensure_no_deflection(
        "I'm happy to pull the latest price ... If you tell me which ticker "
        "you're interested in (e.g., AAPL, TSLA, etc.) ... Just let me know the "
        "symbol and which of those options you'd like.",
        "Since I currently hold SPY stocks, do you think I should continue holding?",
        trail=[],
    )
    assert "⚠ Deflection check" in reply
    assert "SPY" in reply and "get_symbol_briefing" in reply
    assert "model miss, not a missing capability" in reply


def test_deflection_check_stays_silent_when_appropriate():
    from api.chat import ensure_no_deflection

    # tools ran: silent (even if the reply asks a follow-up)
    assert "Deflection" not in ensure_no_deflection(
        "which ticker did you mean?", "should I hold SPY?",
        trail=[{"name": "get_regime", "arguments": {"symbol": "SPY"}}])
    # no ticker named: asking for one is legitimate
    assert "Deflection" not in ensure_no_deflection(
        "let me know the symbol", "can you check a stock for me?", trail=[])
    # ticker named but the reply doesn't ask for one: silent
    assert "Deflection" not in ensure_no_deflection(
        "SPY closed higher.", "should I hold SPY?", trail=[])


def test_the_check_my_portfolio_deflection_is_caught():
    from api.chat import ensure_no_deflection

    reply = ensure_no_deflection(
        "I'd be happy to check your SPY portfolio position! ... How many shares "
        "of SPY do you hold? What's your average purchase price / total cost basis?",
        "can you check my portfolio for a positions on spy",
        trail=[],
    )
    assert "⚠ Deflection check" in reply
    assert "get_portfolio" in reply and "should have looked" in reply


def test_position_details_deflection_needs_portfolio_context():
    from api.chat import ensure_no_deflection

    # asking for cost basis is legitimate when nothing suggests we'd have it
    assert "Deflection" not in ensure_no_deflection(
        "what's your average purchase price?",
        "I bought some gold coins last year", trail=[])
    # and silent when tools actually ran
    assert "Deflection" not in ensure_no_deflection(
        "how many shares do you hold elsewhere?",
        "check my portfolio",
        trail=[{"name": "get_portfolio", "arguments": {}}])


def test_the_denied_portfolio_tool_transcript_is_caught():
    # I011: priming ran (auto_primed in trail) yet the model denied the tool and
    # asked the user to "list the tickers you're holding"
    from api.chat import ensure_no_deflection

    reply = ensure_no_deflection(
        "I don't have a direct tool to pull your full current portfolio positions "
        "list. ... To get started, just list the tickers you're holding "
        "(e.g., AAPL, TSLA, SPY).",
        "can you check my current portfolio positions",
        trail=[{"name": "get_portfolio", "arguments": {"auto_primed": True}}],
    )
    assert "⚠ Deflection check" in reply
    assert "get_portfolio lists your tickers" in reply


def test_fabrication_guard():
    from api.chat import ensure_grounded_numbers

    fabricated = ("SPY last close $777.84, support at 773.75 with 3 touches, "
                  "expected move p95 +3.74%, up-probability 56.6%.")
    # no tools ever, none this turn, numbers not in primed text -> flagged
    flagged = ensure_grounded_numbers(fabricated, [], False, "")
    assert "⚠ Unverified numbers" in flagged
    # the model actually called a tool -> silent
    assert "Unverified" not in ensure_grounded_numbers(
        fabricated, [{"name": "get_regime", "arguments": {"symbol": "SPY"}}],
        False, "")
    # conversation already has tool rows (numbers may come from history) -> silent
    assert "Unverified" not in ensure_grounded_numbers(fabricated, [], True, "")
    # numbers present in the primed snapshot -> grounded -> silent
    primed = "AUTO-FETCHED PORTFOLIO: SPY mv $777.84 ... 773.75 ... +3.74% 56.6%"
    assert "Unverified" not in ensure_grounded_numbers(fabricated, [], False, primed)
    # fewer than 3 precise figures -> silent (casual numbers are fine)
    assert "Unverified" not in ensure_grounded_numbers(
        "SPY rose about 1.20% today.", [], False, "")


def test_human_age():
    assert human_age(28) == "28s"
    assert human_age(840) == "14m"
    assert human_age(7 * 3600 + 52 * 60) == "7h 52m"
    assert human_age(3 * 86400 + 4 * 3600) == "3d 4h"
    assert human_age(-5) == "0s"  # clock skew never yields negative narration
