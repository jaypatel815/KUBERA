"""T110a: holdout_windows + experiment_budgets — Phase 7 preconditions (D029)

Revision ID: c9f6e3a2d874
Revises: b7e4d2c8f1a5
Create Date: 2026-08-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9f6e3a2d874"
down_revision: Union[str, None] = "b7e4d2c8f1a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "holdout_windows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("symbols_json", sa.String(2000), nullable=False),
        sa.Column("start", sa.String(10), nullable=False),
        sa.Column("end", sa.String(10), nullable=False),
        sa.Column("params_hash", sa.String(16), nullable=False),
        sa.Column("state", sa.String(12), nullable=False),
        sa.Column("result_summary", sa.String(1000), nullable=True),
        sa.Column("journal_json", sa.String(4000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "experiment_budgets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("revision", sa.String(64), nullable=False, unique=True),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("attempts_json", sa.String(8000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("experiment_budgets")
    op.drop_table("holdout_windows")
