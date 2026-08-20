"""T122b: research_forecasts — candidate forecasts logged as made

Revision ID: a3d9e8c1f5b7
Revises: e1a7c4f9b2d3
Create Date: 2026-08-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a3d9e8c1f5b7"
down_revision: Union[str, None] = "e1a7c4f9b2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_forecasts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("revision", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(16), nullable=False),
        sa.Column("forecast_date", sa.String(10), nullable=False),
        sa.Column("made_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("basis_close", sa.Float(), nullable=False),
        sa.Column("p05_frac", sa.Float(), nullable=False),
        sa.Column("p50_frac", sa.Float(), nullable=False),
        sa.Column("p95_frac", sa.Float(), nullable=False),
        sa.Column("up_odds", sa.Float(), nullable=False),
        sa.Column("source_note", sa.String(200), nullable=False,
                  server_default=""),
        sa.UniqueConstraint("revision", "symbol", "forecast_date",
                            name="uq_research_forecast"),
    )


def downgrade() -> None:
    op.drop_table("research_forecasts")
