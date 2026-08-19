"""T066: trade_reviews — pre/post-trade coaching reviews persisted per trade

'pre' rows freeze the checklist BEFORE entry so hindsight cannot rewrite it;
'post' rows record expected-vs-actual against the T063 journal entry.

Revision ID: 4f8e2a917c66
Revises: 7c3a91e0d5b2
Create Date: 2026-08-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "4f8e2a917c66"
down_revision: Union[str, None] = "7c3a91e0d5b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trade_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("symbol", sa.String(16), nullable=False),
        sa.Column("journal_id", sa.Integer(), nullable=True),
        sa.Column("attention_count", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.String(8000), nullable=False),
        sa.Column("source", sa.String(24), nullable=False),
    )
    op.create_index("ix_trade_reviews_symbol_ts", "trade_reviews", ["symbol", "ts"])


def downgrade() -> None:
    op.drop_index("ix_trade_reviews_symbol_ts", table_name="trade_reviews")
    op.drop_table("trade_reviews")
