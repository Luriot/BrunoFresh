"""add shopping lists

Revision ID: 20260421_0002
Revises: 20260417_0001
Create Date: 2026-04-21 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260421_0002"
down_revision: Union[str, Sequence[str], None] = "20260417_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shopping_lists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=True),
        sa.Column("needs_review_blob", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shopping_lists_id"), "shopping_lists", ["id"], unique=False)

    op.create_table(
        "shopping_list_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shopping_list_id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=True),
        sa.Column("ingredient_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("is_custom", sa.Boolean(), nullable=False),
        sa.Column("is_already_owned", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"]),
        sa.ForeignKeyConstraint(["shopping_list_id"], ["shopping_lists.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shopping_list_items_category"), "shopping_list_items", ["category"], unique=False)
    op.create_index(op.f("ix_shopping_list_items_id"), "shopping_list_items", ["id"], unique=False)
    op.create_index(op.f("ix_shopping_list_items_ingredient_id"), "shopping_list_items", ["ingredient_id"], unique=False)
    op.create_index(op.f("ix_shopping_list_items_name"), "shopping_list_items", ["name"], unique=False)
    op.create_index(op.f("ix_shopping_list_items_recipe_id"), "shopping_list_items", ["recipe_id"], unique=False)
    op.create_index(op.f("ix_shopping_list_items_shopping_list_id"), "shopping_list_items", ["shopping_list_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_shopping_list_items_shopping_list_id"), table_name="shopping_list_items")
    op.drop_index(op.f("ix_shopping_list_items_recipe_id"), table_name="shopping_list_items")
    op.drop_index(op.f("ix_shopping_list_items_name"), table_name="shopping_list_items")
    op.drop_index(op.f("ix_shopping_list_items_ingredient_id"), table_name="shopping_list_items")
    op.drop_index(op.f("ix_shopping_list_items_id"), table_name="shopping_list_items")
    op.drop_index(op.f("ix_shopping_list_items_category"), table_name="shopping_list_items")
    op.drop_table("shopping_list_items")

    op.drop_index(op.f("ix_shopping_lists_id"), table_name="shopping_lists")
    op.drop_table("shopping_lists")
