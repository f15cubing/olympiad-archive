"""add embedding columns to problems (semantic search, Phase C)

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("problems") as batch_op:
        batch_op.add_column(sa.Column("embedding", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("embedding_model", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("embedded_at", sa.TIMESTAMP(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("problems") as batch_op:
        batch_op.drop_column("embedded_at")
        batch_op.drop_column("embedding_model")
        batch_op.drop_column("embedding")
