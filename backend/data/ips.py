"""Investment Policy Statement access (T061). Single row, deliberate updates only."""

import json

from sqlalchemy.orm import Session

from data.models import InvestmentPolicy, utcnow

IPS_ID = 1


def get_ips(session: Session) -> InvestmentPolicy | None:
    return session.get(InvestmentPolicy, IPS_ID)


def upsert_ips(session: Session, **fields) -> InvestmentPolicy:
    """Partial update: only provided (non-None) fields change. Lists REPLACE wholesale
    (deterministic semantics — 'my restrictions are now exactly these')."""
    row = session.get(InvestmentPolicy, IPS_ID)
    if row is None:
        row = InvestmentPolicy(id=IPS_ID)
        session.add(row)
    for key in ("objectives", "target_annual_return_frac", "max_drawdown_frac",
                "horizon_years", "risk_tolerance", "notes"):
        if fields.get(key) is not None:
            setattr(row, key, fields[key])
    if fields.get("restrictions") is not None:
        row.restrictions_json = json.dumps(list(fields["restrictions"]))
    if fields.get("prohibited_strategies") is not None:
        row.prohibited_strategies_json = json.dumps(list(fields["prohibited_strategies"]))
    row.updated_at = utcnow()
    session.commit()
    return row


def ips_as_dict(row: InvestmentPolicy) -> dict:
    return {
        "objectives": row.objectives,
        "target_annual_return_frac": row.target_annual_return_frac,
        "max_drawdown_frac": row.max_drawdown_frac,
        "horizon_years": row.horizon_years,
        "risk_tolerance": row.risk_tolerance,
        "restrictions": json.loads(row.restrictions_json or "[]"),
        "prohibited_strategies": json.loads(row.prohibited_strategies_json or "[]"),
        "notes": row.notes,
        "updated_at": row.updated_at.isoformat(),
    }


def format_ips_for_prompt(row: InvestmentPolicy) -> str:
    """Compact, deterministic context block for the system prompt."""
    parts: list[str] = []
    if row.objectives:
        parts.append(f"Objectives: {row.objectives}")
    if row.target_annual_return_frac is not None:
        parts.append(f"Target return: {row.target_annual_return_frac:.1%}/yr")
    if row.max_drawdown_frac is not None:
        parts.append(f"Max acceptable drawdown: {row.max_drawdown_frac:.1%}")
    if row.horizon_years is not None:
        parts.append(f"Horizon: {row.horizon_years:g} years")
    if row.risk_tolerance:
        parts.append(f"Risk tolerance: {row.risk_tolerance}")
    restrictions = json.loads(row.restrictions_json or "[]")
    if restrictions:
        parts.append("Restrictions: " + "; ".join(restrictions))
    prohibited = json.loads(row.prohibited_strategies_json or "[]")
    if prohibited:
        parts.append("Prohibited strategies: " + "; ".join(prohibited))
    if row.notes:
        parts.append(f"Notes: {row.notes}")
    if not parts:
        return ""
    return (
        "OWNER'S INVESTMENT POLICY STATEMENT (hard context — check every "
        "recommendation against it and state conflicts plainly):\n" + " | ".join(parts)
    )
