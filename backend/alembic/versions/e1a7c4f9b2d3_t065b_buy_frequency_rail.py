"""T065b: order-frequency rail memory on risk_state (buys_day, buys_today)

Revision ID: e1a7c4f9b2d3
Revises: c9f6e3a2d874
Create Date: 2026-08-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1a7c4f9b2d3"
down_revision: Union[str, None] = "c9f6e3a2d874"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("risk_state", sa.Column("buys_day", sa.String(10),
                                          nullable=True))
    op.add_column("risk_state", sa.Column("buys_today", sa.Integer(),
                                          nullable=False,
                                          server_default="0"))


def downgrade() -> None:
    op.drop_column("risk_state", "buys_today")
    op.drop_column("risk_state", "buys_day")
