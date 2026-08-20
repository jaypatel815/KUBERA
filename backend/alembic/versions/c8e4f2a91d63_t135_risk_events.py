"""T135: risk_events — tier changes and breaker trips, observed and kept

Revision ID: c8e4f2a91d63
Revises: a3d9e8c1f5b7
Create Date: 2026-08-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8e4f2a91d63"
down_revision: Union[str, None] = "a3d9e8c1f5b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "risk_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("detail", sa.String(400), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("risk_events")
