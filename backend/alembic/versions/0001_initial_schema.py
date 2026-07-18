"""initial schema

Baseline matching backend/models.py as of the pre-Alembic state (tables were created
with Base.metadata.create_all). For an existing create_all database, stamp this revision
(`alembic stamp 0001`) before upgrading; a fresh database builds from here.

Revision ID: 0001
Revises:
Create Date: 2026-07-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "competitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_competitions_id", "competitions", ["id"])

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_tags_id", "tags", ["id"])

    op.create_table(
        "problems",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("competition_id", sa.Integer(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("problem_number", sa.Integer(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=True),
        sa.Column("ai_metadata", sa.JSON(), nullable=True),
        sa.Column("tagged_at", sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(["competition_id"], ["competitions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_problems_id", "problems", ["id"])

    op.create_table(
        "solutions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("problem_id", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_solutions_id", "solutions", ["id"])

    op.create_table(
        "problem_tags",
        sa.Column("problem_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("problem_id", "tag_id"),
    )


def downgrade() -> None:
    op.drop_table("problem_tags")
    op.drop_index("ix_solutions_id", table_name="solutions")
    op.drop_table("solutions")
    op.drop_index("ix_problems_id", table_name="problems")
    op.drop_table("problems")
    op.drop_index("ix_tags_id", table_name="tags")
    op.drop_table("tags")
    op.drop_index("ix_competitions_id", table_name="competitions")
    op.drop_table("competitions")
