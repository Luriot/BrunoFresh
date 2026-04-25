"""add is_favorite to recipes and pantry_items table

Revision ID: 20260425_0004
Revises: 20260422_0003
Create Date: 2026-04-25 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260425_0004"
down_revision: Union[str, Sequence[str], None] = "20260422_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("recipes", sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table(
        "pantry_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("name_fr", sa.String(length=200), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pantry_items_id"), "pantry_items", ["id"], unique=False)
    op.create_index(op.f("ix_pantry_items_ingredient_id"), "pantry_items", ["ingredient_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_pantry_items_ingredient_id"), table_name="pantry_items")
    op.drop_index(op.f("ix_pantry_items_id"), table_name="pantry_items")
    op.drop_table("pantry_items")
    op.drop_column("recipes", "is_favorite")
