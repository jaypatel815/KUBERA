"""T152: household tables — debts, recurring flows, spending (D039 Phase 9)

Revision ID: d4b8f1a6c2e5
Revises: c8e4f2a91d63
Create Date: 2026-08-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4b8f1a6c2e5"
down_revision: Union[str, None] = "c8e4f2a91d63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "debts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("balance", sa.Float(), nullable=False),
        sa.Column("apr_frac", sa.Float(), nullable=False),
        sa.Column("min_payment", sa.Float(), nullable=False),
        sa.Column("credit_limit", sa.Float(), nullable=True),
        sa.Column("due_day", sa.Integer(), nullable=True),
        sa.Column("balance_asof", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "recurring_flows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("cadence", sa.String(16), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "spending_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("note", sa.String(200), nullable=True),
        sa.Column("source", sa.String(8), nullable=False),
        sa.Column("import_key", sa.String(120), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("spending_entries")
    op.drop_table("recurring_flows")
    op.drop_table("debts")
