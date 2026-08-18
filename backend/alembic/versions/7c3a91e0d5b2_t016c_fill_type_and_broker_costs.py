"""T016c: fill_type + broker-reported commission/fees on transactions

Schwab real fills carry option-ness (qty = CONTRACTS, 100x multiplier —
consumers must not treat a contract as a share, I020) and the broker's own
per-trade costs from transferItems. Legacy rows stay NULL = equity, no cost
data — never backfilled with guesses.

Revision ID: 7c3a91e0d5b2
Revises: 00c4e1efd5c4
Create Date: 2026-08-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7c3a91e0d5b2"
down_revision: Union[str, None] = "00c4e1efd5c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("fill_type", sa.String(16), nullable=True))
    op.add_column("transactions", sa.Column("commission", sa.Float(), nullable=True))
    op.add_column("transactions", sa.Column("fees", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("transactions", "fees")
    op.drop_column("transactions", "commission")
    op.drop_column("transactions", "fill_type")
