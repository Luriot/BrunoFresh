"""add ingredient_translations table

Revision ID: 20260425_0007
Revises: 20260425_0006
Create Date: 2026-04-25 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260425_0007"
down_revision: Union[str, Sequence[str], None] = "20260425_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingredient_translations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column("lang_code", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("ingredient_id", "lang_code", name="uq_ingredient_lang"),
    )
    op.create_index(
        op.f("ix_ingredient_translations_ingredient_id"),
        "ingredient_translations",
        ["ingredient_id"],
        unique=False,
    )

    # Populate from existing bilingual columns on the ingredients table
    op.execute(
        "INSERT INTO ingredient_translations (ingredient_id, lang_code, name) "
        "SELECT id, 'en', name_en FROM ingredients"
    )
    op.execute(
        "INSERT INTO ingredient_translations (ingredient_id, lang_code, name) "
        "SELECT id, 'fr', name_fr FROM ingredients "
        "WHERE name_fr IS NOT NULL AND name_fr != ''"
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_ingredient_translations_ingredient_id"),
        table_name="ingredient_translations",
    )
    op.drop_table("ingredient_translations")
