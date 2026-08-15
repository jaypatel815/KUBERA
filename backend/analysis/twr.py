"""Time-weighted return (T060) — the number that survives a deposit.

Simple return (end/start − 1) answers "how much more money is in the account",
which is NOT "how well did the strategy do". Deposit $500 into a $1,000
account and the naive figure prints +50% while the manager did nothing.
Comparing that to SPY is a lie in the owner's favor — the worst direction.

TWR removes the effect of money moving in or out by cutting the history at
each external flow, measuring each sub-period on its own, and CHAIN-LINKING:

    TWR = Π (V_end_i / (V_start_i + flow_i)) − 1

Convention (stated because it changes the answer): a flow dated D is treated
as arriving at the START of D — the day's return is measured on the capital
that was actually working that day.

Pure functions. Money math, hand-tested, never LLM-computed.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SubPeriod:
    start_date: str
    end_date: str
    start_value: float
    flow: float          # external cash in (+) / out (−) applied at start
    end_value: float
    return_frac: float


@dataclass(frozen=True)
class TWRResult:
    twr_frac: float          # chain-linked time-weighted return
    simple_return_frac: float  # naive end/start − 1, for the contrast
    net_flows: float
    n_flows: int
    sub_periods: list = field(default_factory=list)
    note: str = ""


def time_weighted_return(values: list[tuple[str, float]],
                         flows: list[tuple[str, float]] | None = None) -> TWRResult:
    """`values`: [(date, equity)] chronological, at least 2 points.
    `flows`: [(date, amount)] external deposits (+) / withdrawals (−).
    Flows on dates outside the value range are ignored (with a note)."""
    if len(values) < 2:
        raise ValueError("need at least 2 equity points")
    dates = [d for d, _ in values]
    if dates != sorted(dates):
        raise ValueError("values must be chronological")
    if any(v <= 0 for _, v in values):
        raise ValueError("equity values must be positive")

    flow_by_date: dict[str, float] = {}
    ignored = 0
    for d, amt in (flows or []):
        if d <= dates[0] or d > dates[-1]:
            ignored += 1          # before the window opens or after it closes
            continue
        flow_by_date[d] = flow_by_date.get(d, 0.0) + amt

    subs: list[SubPeriod] = []
    linked = 1.0
    for i in range(1, len(values)):
        d0, v0 = values[i - 1]
        d1, v1 = values[i]
        flow = flow_by_date.get(d1, 0.0)
        base = v0 + flow
        if base <= 0:
            raise ValueError(
                f"non-positive invested base on {d1} (equity {v0} + flow {flow}) "
                "— cannot measure a return on nothing")
        r = v1 / base - 1.0
        linked *= 1.0 + r
        subs.append(SubPeriod(d0, d1, v0, flow, v1, round(r, 6)))

    net = sum(flow_by_date.values())
    simple = values[-1][1] / values[0][1] - 1.0
    note = ""
    if not flow_by_date:
        note = ("no external flows in this window — TWR equals the simple "
                "return; the distinction starts mattering on the first deposit")
    elif abs(simple - (linked - 1.0)) > 1e-9:
        note = ("external flows detected: the simple return is inflated/deflated "
                "by money moving in or out — compare TWR to the benchmark, "
                "never the simple figure")
    if ignored:
        note += f" ({ignored} flow(s) outside the window ignored)"
    return TWRResult(
        twr_frac=round(linked - 1.0, 6),
        simple_return_frac=round(simple, 6),
        net_flows=round(net, 2),
        n_flows=len(flow_by_date),
        sub_periods=subs,
        note=note,
    )
