"""add bilingual ingredient names and shopping list recipe links

Revision ID: 20260422_0003
Revises: 20260421_0002
Create Date: 2026-04-22 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260422_0003"
down_revision: Union[str, Sequence[str], None] = "20260421_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ingredients", sa.Column("name_fr", sa.String(length=200), nullable=True))
    op.add_column("shopping_list_items", sa.Column("name_fr", sa.String(length=200), nullable=True))

    op.create_table(
        "shopping_list_recipes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shopping_list_id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("target_servings", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"]),
        sa.ForeignKeyConstraint(["shopping_list_id"], ["shopping_lists.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shopping_list_recipes_id"), "shopping_list_recipes", ["id"], unique=False)
    op.create_index(
        op.f("ix_shopping_list_recipes_recipe_id"),
        "shopping_list_recipes",
        ["recipe_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_shopping_list_recipes_shopping_list_id"),
        "shopping_list_recipes",
        ["shopping_list_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_shopping_list_recipes_shopping_list_id"), table_name="shopping_list_recipes")
    op.drop_index(op.f("ix_shopping_list_recipes_recipe_id"), table_name="shopping_list_recipes")
    op.drop_index(op.f("ix_shopping_list_recipes_id"), table_name="shopping_list_recipes")
    op.drop_table("shopping_list_recipes")

    op.drop_column("shopping_list_items", "name_fr")
    op.drop_column("ingredients", "name_fr")
