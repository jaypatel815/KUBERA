"""I007 defenses — the symbol-alignment post-check (from a real transcript where
'should I buy SPY' was answered with a TSLA sizing table) and human-readable ages."""


from api.chat import _user_tickers, ensure_symbol_alignment
from data.market_data import human_age


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


def test_human_age():
    assert human_age(28) == "28s"
    assert human_age(840) == "14m"
    assert human_age(7 * 3600 + 52 * 60) == "7h 52m"
    assert human_age(3 * 86400 + 4 * 3600) == "3d 4h"
    assert human_age(-5) == "0s"  # clock skew never yields negative narration
