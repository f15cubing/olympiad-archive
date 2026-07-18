"""unique (competition_id, year, problem_number) on problems

Enforces one row per contest problem so the bulk importer can upsert on this key.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-17
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT = "uq_problem_comp_year_number"
COLUMNS = ["competition_id", "year", "problem_number"]


def upgrade() -> None:
    # batch mode recreates the table on SQLite (which can't ALTER ADD CONSTRAINT).
    with op.batch_alter_table("problems") as batch_op:
        batch_op.create_unique_constraint(CONSTRAINT, COLUMNS)


def downgrade() -> None:
    with op.batch_alter_table("problems") as batch_op:
        batch_op.drop_constraint(CONSTRAINT, type_="unique")
