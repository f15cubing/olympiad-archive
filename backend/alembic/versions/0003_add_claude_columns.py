"""add claude_metadata + claude_tagged_at to problems

Non-destructive Claude tagging columns (Phase D). Gemini's ai_metadata/tagged_at are
untouched; Claude tags land here so the two providers can be compared per problem.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("problems") as batch_op:
        batch_op.add_column(sa.Column("claude_metadata", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("claude_tagged_at", sa.TIMESTAMP(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("problems") as batch_op:
        batch_op.drop_column("claude_tagged_at")
        batch_op.drop_column("claude_metadata")
