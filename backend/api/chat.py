"""The conversation loop (T042): persona + history → LLM → tools → grounded answer.

Every user message, assistant reply, tool call, and tool result is persisted with a
timestamp — "why did KUBERA say that" is always answerable from chat_messages alone.
Tool failures are surfaced to the model verbatim (the persona requires honest reporting),
never swallowed. The loop is bounded: max_tool_rounds prevents runaway tool chains.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.context import assemble_context
from api.persona import build_system_prompt
from api.tools import ConfirmationRequiredError, ToolContext, ToolError, registry
from data.ips import format_ips_for_prompt, get_ips
from data.models import ChatMessage, Conversation
from settings import get_settings

log = logging.getLogger("kubera.chat")

MAX_TOOL_ROUNDS = 6
MAX_STORED_CHARS = 6000  # tool results are capped before storage and LLM replay


@dataclass(frozen=True)
class ChatTurnResult:
    conversation_id: int
    reply: str
    tool_trail: list[dict] = field(default_factory=list)  # [{"name", "arguments"}]
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = "end"


def _cap(text: str, limit: int = MAX_STORED_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"... [truncated at {limit} chars]"


_RECENCY_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}|as of", re.IGNORECASE)

# Symbol-alignment post-check (I007): a real transcript showed the model answering a
# question about SPY by sizing TSLA. The tool layer echoed what it was asked — the
# model misdirected it. Deterministic guard: if the user NAMED tickers and every
# tool call used different ones, flag the reply. Conservative by design: no tickers
# named, or any overlap -> silent.
_TICKER_PATTERN = re.compile(r"\$([A-Za-z]{1,5})\b|\b([A-Z]{2,5})\b")
_TICKER_STOPWORDS = frozenset({
    "OK", "US", "USA", "ETF", "AI", "PM", "AM", "CEO", "IPO", "FED", "CPI", "GDP",
    "YTD", "EOD", "RSI", "SMA", "ATR", "VWAP", "IPS", "DQS", "USD", "BUY", "SELL",
    "HOLD", "THE", "AND", "FOR", "NOT", "ALL", "CAN", "DID", "YES", "NO", "DO",
    "IF", "IS", "IT", "ME", "MY", "OF", "ON", "OR", "SO", "TO", "UP", "WE", "GO",
    "IMO", "LOL", "ASAP", "TODAY", "NOW",
})


def _user_tickers(text: str) -> set[str]:
    out: set[str] = set()
    for m in _TICKER_PATTERN.finditer(text):
        dollar, bare = m.group(1), m.group(2)
        if dollar:
            out.add(dollar.upper())  # $spy is always a ticker claim
        elif bare and bare not in _TICKER_STOPWORDS:
            out.add(bare)
    return out


def ensure_symbol_alignment(reply: str, user_text: str, trail: list[dict]) -> str:
    """Post-check (I007): the user named tickers; did the tools run for ANY of them?"""
    asked = _user_tickers(user_text)
    used = {
        str(t["arguments"]["symbol"]).upper()
        for t in trail
        if isinstance(t.get("arguments"), dict) and t["arguments"].get("symbol")
    }
    if not asked or not used or (asked & used):
        return reply
    return (
        f"{reply}\n\n_⚠ Symbol check: you asked about {', '.join(sorted(asked))} but "
        f"the tools ran for {', '.join(sorted(used))}. This answer may be misdirected "
        "— please re-ask, naming the symbol._"
    )


# Deflection post-check (I008/I010): real transcripts showed "I hold SPY, should I
# keep holding?" answered with "tell me which ticker", and "check my portfolio for
# SPY" answered with "how many shares do you hold?" — both with ZERO tool calls.
_ASKS_FOR_SYMBOL = re.compile(
    r"which (ticker|symbol)|let me know (the|which) (ticker|symbol)"
    r"|tell me (which|the) (ticker|symbol)|what (ticker|symbol)"
    r"|know the symbol|name the (ticker|symbol)",
    re.IGNORECASE,
)
_ASKS_FOR_POSITION_DETAILS = re.compile(
    r"how many shares|share count|cost basis|average (purchase|entry) price"
    r"|purchase price|amount invested|what('s| is) your (entry|average)",
    re.IGNORECASE,
)
_PORTFOLIO_INTENT = re.compile(
    r"\b(my|our) (portfolio|positions?|holdings?|account)\b"
    r"|do i (hold|own)|am i (invested|holding)|check my",
    re.IGNORECASE,
)


def ensure_no_deflection(reply: str, user_text: str, trail: list[dict]) -> str:
    """The user gave what was needed and got asked for it back, with no data touched."""
    if trail:
        return reply
    asks_symbol = bool(_ASKS_FOR_SYMBOL.search(reply))
    asks_position = bool(_ASKS_FOR_POSITION_DETAILS.search(reply))
    asked = _user_tickers(user_text)
    portfolioish = bool(_PORTFOLIO_INTENT.search(user_text))

    if asks_position and (portfolioish or asked):
        return (
            f"{reply}\n\n_⚠ Deflection check: your positions, share counts, and "
            "cost basis are ALREADY available via get_portfolio — KUBERA should "
            "have looked instead of asking. A model miss, not a missing "
            "capability. Re-ask, or switch to the claude-sdk brain._"
        )
    if asks_symbol and asked:
        named = ", ".join(sorted(asked))
        return (
            f"{reply}\n\n_⚠ Deflection check: you already named {named}. KUBERA has "
            "the tools to answer this (get_symbol_briefing for recent performance, "
            "get_regime, get_exit_plan, triage_position if you hold it) but called "
            "none of them — a model miss, not a missing capability. Re-ask, or "
            "switch to the claude-sdk brain for real decisions._"
        )
    return reply


def prime_portfolio(system: str, user_text: str, ctx: ToolContext,
                    trail: list[dict], tool_asofs: dict[str, str]) -> str:
    """I010: when the user asks about THEIR portfolio, fetch it server-side and put
    the data in front of the model — deflection becomes structurally impossible.
    Deterministic, audited via the trail; silent no-op when intent or broker absent."""
    if not _PORTFOLIO_INTENT.search(user_text) or ctx.alpaca is None:
        return system
    try:
        result = registry.execute("get_portfolio", {}, ctx)
    except ToolError as e:
        log.warning("portfolio priming skipped: %s", e)
        return system
    positions = result.get("positions") or []
    lines = [
        f"- {p['symbol']}: {p['qty']} sh @ avg "
        f"{(p['cost_basis'] / p['qty']) if p['qty'] else 0.0:.2f} "
        f"(mv {p['market_value']:.2f}, unrealized {p['unrealized_pl']:+.2f})"
        for p in positions[:8]
    ] or ["- (no open positions)"]
    acct = result.get("account", {})
    snapshot = (
        "\n\nAUTO-FETCHED PORTFOLIO (server-side, this turn; asof "
        f"{result.get('asof', 'unknown')}):\n"
        f"equity {acct.get('equity')}, cash {acct.get('cash')}\n"
        + "\n".join(lines)
        + "\nAnswer from THIS data. Do NOT ask the user for share counts, cost "
        "basis, or entry prices — they are above."
    )
    trail.append({"name": "get_portfolio", "arguments": {"auto_primed": True}})
    if result.get("asof"):
        tool_asofs["get_portfolio"] = str(result["asof"])
    log.info("portfolio primed into system prompt (%d positions)", len(positions))
    return system + snapshot


def ensure_recency_line(reply: str, tool_asofs: dict[str, str]) -> str:
    """Post-check (T043): a data-grounded reply must carry a date. If the model used
    tools but stated no recency, append a deterministic footer from the ACTUAL tool
    timestamps — enforced by code, not trusted to the prompt."""
    if not tool_asofs or _RECENCY_PATTERN.search(reply):
        return reply
    parts = "; ".join(f"{name} asof {asof}" for name, asof in sorted(tool_asofs.items()))
    return f"{reply}\n\n_Data recency: {parts}_"


def _history(db: Session, conversation_id: int) -> list[dict]:
    """DB rows -> neutral message format, oldest first."""
    rows = db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.id)
    ).scalars().all()
    neutral: list[dict] = []
    for r in rows:
        if r.role == "user":
            neutral.append({"role": "user", "content": r.content or ""})
        elif r.role == "assistant":
            m: dict = {"role": "assistant", "content": r.content}
            if r.tool_calls_json:
                m["tool_calls"] = json.loads(r.tool_calls_json)
            neutral.append(m)
        elif r.role == "tool":
            neutral.append({
                "role": "tool", "tool_call_id": r.tool_call_id or "",
                "name": r.tool_name or "", "content": r.content or "",
            })
    return neutral


def run_chat_turn(
    db: Session,
    provider,
    ctx: ToolContext,
    user_text: str,
    conversation_id: int | None = None,
    max_tool_rounds: int = MAX_TOOL_ROUNDS,
    voice: bool = False,
) -> ChatTurnResult:
    if not user_text.strip():
        raise ValueError("empty message")

    if conversation_id is None:
        convo = Conversation(title=_cap(user_text, 118))
        db.add(convo)
        db.flush()
        conversation_id = convo.id
    elif db.get(Conversation, conversation_id) is None:
        raise ValueError(f"unknown conversation_id {conversation_id}")

    db.add(ChatMessage(conversation_id=conversation_id, role="user", content=_cap(user_text)))
    db.commit()

    ips_row = get_ips(db)
    system = build_system_prompt(
        datetime.now(timezone.utc).isoformat(), registry.names(), voice=voice,
        ips_context=format_ips_for_prompt(ips_row) if ips_row else None,
    )
    schemas = registry.schemas()
    trail: list[dict] = []
    tool_asofs: dict[str, str] = {}  # tool name -> asof from its actual result
    system = prime_portfolio(system, user_text, ctx, trail, tool_asofs)  # I010
    total_in = total_out = 0
    reply = None

    # SDK-style providers execute tools inside complete(); hand them the request-bound
    # context (confirmation gate included) and collect their audit events afterward.
    if hasattr(provider, "tool_context"):
        provider.tool_context = ctx

    budget = get_settings().context_budget_chars
    for _round in range(max_tool_rounds):
        history = assemble_context(_history(db, conversation_id), budget)
        reply = provider.complete(system, history, schemas)

        for ev in (getattr(provider, "last_tool_events", None) or []):
            trail.append({"name": ev["name"], "arguments": ev["arguments"]})
            if ev.get("asof"):
                tool_asofs[ev["name"]] = ev["asof"]
            db.add(ChatMessage(
                conversation_id=conversation_id, role="tool",
                tool_call_id=ev["id"], tool_name=ev["name"],
                content=_cap(ev["content"]),
            ))
        if getattr(provider, "last_tool_events", None):
            provider.last_tool_events = []
            db.commit()
        total_in += reply.input_tokens
        total_out += reply.output_tokens

        db.add(ChatMessage(
            conversation_id=conversation_id, role="assistant",
            content=_cap(reply.text) if reply.text else None,
            tool_calls_json=json.dumps(
                [{"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                 for tc in reply.tool_calls]
            ) if reply.wants_tools else None,
            input_tokens=reply.input_tokens, output_tokens=reply.output_tokens,
        ))
        db.commit()

        if not reply.wants_tools:
            return ChatTurnResult(
                conversation_id=conversation_id,
                reply=ensure_no_deflection(
                    ensure_symbol_alignment(
                        ensure_recency_line(reply.text or "", tool_asofs),
                        user_text, trail,
                    ),
                    user_text, trail,
                ),
                tool_trail=trail, input_tokens=total_in, output_tokens=total_out,
                stop_reason=reply.stop_reason,
            )

        for tc in reply.tool_calls:
            trail.append({"name": tc.name, "arguments": tc.arguments})
            try:
                result = registry.execute(tc.name, tc.arguments, ctx)
                asof_val = result.get("asof")
                if asof_val is not None:  # str for most tools, datetime for dataclass dumps
                    tool_asofs[tc.name] = (
                        asof_val.isoformat() if hasattr(asof_val, "isoformat")
                        else str(asof_val)
                    )
                content = _cap(json.dumps(result, default=str))
            except ConfirmationRequiredError as e:
                # Not an error: the user must confirm out-of-band. Tell the model so it
                # can ask; it cannot confirm on the user's behalf (ctx is request-bound).
                content = json.dumps({"confirmation_required": True, "message": str(e)})
                log.info("tool %s awaiting user confirmation", tc.name)
            except ToolError as e:
                content = json.dumps({"error": str(e)})
                log.warning("tool %s failed in chat: %s", tc.name, e)
            db.add(ChatMessage(
                conversation_id=conversation_id, role="tool",
                tool_call_id=tc.id, tool_name=tc.name, content=content,
            ))
        db.commit()

    # Bounded loop exhausted: return honestly rather than spinning.
    return ChatTurnResult(
        conversation_id=conversation_id,
        reply=ensure_symbol_alignment(
            ensure_recency_line(
                (reply.text if reply and reply.text else
                 f"(stopped after {max_tool_rounds} tool rounds without a final answer)"),
                tool_asofs,
            ),
            user_text, trail,
        ),
        tool_trail=trail, input_tokens=total_in, output_tokens=total_out,
        stop_reason="max_tool_rounds",
    )
