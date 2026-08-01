"""ingredient merge rules

Revision ID: 20260801_0015
Revises: 20260731_0014
Create Date: 2026-08-01 00:00:00

Adds the ``ingredient_merge_rules`` table: persistent admin decisions mapping an
incoming ingredient name to a canonical Ingredient row so future scrapes do not
re-create duplicates the admin already merged. ``source_name_key`` is the
lower-stripped alias with a unique index so two rules cannot cover the same
alias; the canonical FK cascades on delete.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260801_0015"
down_revision: Union[str, Sequence[str], None] = "20260731_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingredient_merge_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_name", sa.String(length=200), nullable=False),
        sa.Column("source_name_key", sa.String(length=200), nullable=False),
        sa.Column(
            "canonical_ingredient_id",
            sa.Integer(),
            sa.ForeignKey("ingredients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category_hint", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        op.f("ix_ingredient_merge_rules_source_name_key"),
        "ingredient_merge_rules",
        ["source_name_key"],
        unique=True,
    )
    op.create_index(
        op.f("ix_ingredient_merge_rules_id"),
        "ingredient_merge_rules",
        ["id"],
    )
    op.create_index(
        op.f("ix_ingredient_merge_rules_canonical_ingredient_id"),
        "ingredient_merge_rules",
        ["canonical_ingredient_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ingredient_merge_rules_canonical_ingredient_id"), table_name="ingredient_merge_rules")
    op.drop_index(op.f("ix_ingredient_merge_rules_id"), table_name="ingredient_merge_rules")
    op.drop_index(op.f("ix_ingredient_merge_rules_source_name_key"), table_name="ingredient_merge_rules")
    op.drop_table("ingredient_merge_rules")