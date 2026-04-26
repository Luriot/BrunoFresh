"""add instruction_steps_json to recipes

Revision ID: 20260426_0008
Revises: 20260425_0007
Create Date: 2026-04-26 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260426_0008"
down_revision: Union[str, Sequence[str], None] = "20260425_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("recipes", sa.Column("instruction_steps_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("recipes", "instruction_steps_json")
