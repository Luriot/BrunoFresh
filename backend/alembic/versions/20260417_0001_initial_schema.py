"""initial schema

Revision ID: 20260417_0001
Revises: 
Create Date: 2026-04-17 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260417_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingredients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name_en", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("is_normalized", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ingredients_category"), "ingredients", ["category"], unique=False)
    op.create_index(op.f("ix_ingredients_id"), "ingredients", ["id"], unique=False)
    op.create_index(op.f("ix_ingredients_name_en"), "ingredients", ["name_en"], unique=True)

    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("source_domain", sa.String(length=120), nullable=False),
        sa.Column("image_local_path", sa.String(length=512), nullable=True),
        sa.Column("image_original_url", sa.String(length=1024), nullable=True),
        sa.Column("instructions_text", sa.Text(), nullable=False),
        sa.Column("base_servings", sa.Integer(), nullable=False),
        sa.Column("prep_time_minutes", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recipes_id"), "recipes", ["id"], unique=False)
    op.create_index(op.f("ix_recipes_source_domain"), "recipes", ["source_domain"], unique=False)
    op.create_index(op.f("ix_recipes_title"), "recipes", ["title"], unique=False)
    op.create_index(op.f("ix_recipes_url"), "recipes", ["url"], unique=True)

    op.create_table(
        "scrape_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.String(length=800), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scrape_jobs_id"), "scrape_jobs", ["id"], unique=False)
    op.create_index(op.f("ix_scrape_jobs_status"), "scrape_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_scrape_jobs_url"), "scrape_jobs", ["url"], unique=False)

    op.create_table(
        "recipe_ingredients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=True),
        sa.Column("raw_string", sa.String(length=400), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=False),
        sa.Column("needs_review", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recipe_ingredients_id"), "recipe_ingredients", ["id"], unique=False)
    op.create_index(op.f("ix_recipe_ingredients_recipe_id"), "recipe_ingredients", ["recipe_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_recipe_ingredients_recipe_id"), table_name="recipe_ingredients")
    op.drop_index(op.f("ix_recipe_ingredients_id"), table_name="recipe_ingredients")
    op.drop_table("recipe_ingredients")

    op.drop_index(op.f("ix_scrape_jobs_url"), table_name="scrape_jobs")
    op.drop_index(op.f("ix_scrape_jobs_status"), table_name="scrape_jobs")
    op.drop_index(op.f("ix_scrape_jobs_id"), table_name="scrape_jobs")
    op.drop_table("scrape_jobs")

    op.drop_index(op.f("ix_recipes_url"), table_name="recipes")
    op.drop_index(op.f("ix_recipes_title"), table_name="recipes")
    op.drop_index(op.f("ix_recipes_source_domain"), table_name="recipes")
    op.drop_index(op.f("ix_recipes_id"), table_name="recipes")
    op.drop_table("recipes")

    op.drop_index(op.f("ix_ingredients_name_en"), table_name="ingredients")
    op.drop_index(op.f("ix_ingredients_id"), table_name="ingredients")
    op.drop_index(op.f("ix_ingredients_category"), table_name="ingredients")
    op.drop_table("ingredients")
