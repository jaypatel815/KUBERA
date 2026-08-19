"""T083: earnings_observed — self-accumulated earnings history

The owner's probe (2026-08-18) measured FMP past-calendar windows as
PAYWALLED on the free tier; the forward window answers. This table records
forward-window dates BEFORE they happen so base rates build from KUBERA's
own observations.

Revision ID: 9d1c5b3fa284
Revises: 4f8e2a917c66
Create Date: 2026-08-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9d1c5b3fa284"
down_revision: Union[str, None] = "4f8e2a917c66"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "earnings_observed",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(16), nullable=False),
        sa.Column("event_date", sa.String(10), nullable=False),
        sa.Column("time_hint", sa.String(16), nullable=True),
        sa.Column("eps_estimated", sa.Float(), nullable=True),
        sa.Column("eps_actual", sa.Float(), nullable=True),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(24), nullable=False),
        sa.UniqueConstraint("symbol", "event_date", name="uq_earnings_symbol_date"),
    )


def downgrade() -> None:
    op.drop_table("earnings_observed")
