"""T065: risk_state gains disabled_symbols_json — buys refused, sells exempt

Revision ID: b7e4d2c8f1a5
Revises: 9d1c5b3fa284
Create Date: 2026-08-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7e4d2c8f1a5"
down_revision: Union[str, None] = "9d1c5b3fa284"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("risk_state", sa.Column(
        "disabled_symbols_json", sa.String(2000), nullable=False,
        server_default="[]"))


def downgrade() -> None:
    op.drop_column("risk_state", "disabled_symbols_json")
