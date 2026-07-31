"""ingredient pack overrides (grams_per_paquet, grams_per_boite)

Revision ID: 20260731_0014
Revises: 20260726_0013
Create Date: 2026-07-31 00:00:00

Adds two nullable Float columns to ``ingredients`` so an admin can pin the
grams-per-unit for a ``paquet`` / ``boîte`` of a specific ingredient. When null,
the aggregator falls back to retro-calibration from the raw string, then to the
static ``_PACK_GRAMS`` table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260731_0014"
down_revision: Union[str, Sequence[str], None] = "20260726_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("ingredients") as batch_op:
        batch_op.add_column(sa.Column("grams_per_paquet", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("grams_per_boite", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("ingredients") as batch_op:
        batch_op.drop_column("grams_per_boite")
        batch_op.drop_column("grams_per_paquet")