"""model drift fix: ix_ingredient_translations_id, drop uq_ingredient_lang

Revision ID: 20260726_0013
Revises: a36c149a93d4
Create Date: 2026-07-26 00:00:00

Closes the model-vs-schema drift that `alembic check` reported at head
revision a36c149a93d4:

1. `IngredientTranslation.id` is declared with `index=True` in
   app/models.py but the matching index was never created by any prior
   migration. Add it.

2. `20260425_0007` created a `UniqueConstraint("ingredient_id",
   "lang_code", name="uq_ingredient_lang")` on `ingredient_translations`,
   but the current `IngredientTranslation` model no longer declares it.
   Drop it so the schema matches the model. Uses `batch_alter_table`
   because SQLite can't drop a constraint directly.

Both ops are SQLite-safe (CREATE INDEX + batch drop unique constraint).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260726_0013"
down_revision: Union[str, Sequence[str], None] = "a36c149a93d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    existing_indexes = {i["name"] for i in insp.get_indexes("ingredient_translations")}
    if "ix_ingredient_translations_id" not in existing_indexes:
        op.create_index(
            op.f("ix_ingredient_translations_id"),
            "ingredient_translations",
            ["id"],
            unique=False,
        )

    existing_uqs = {
        (u.get("name") or "")
        for u in insp.get_unique_constraints("ingredient_translations")
    }
    if "uq_ingredient_lang" in existing_uqs:
        with op.batch_alter_table("ingredient_translations") as batch_op:
            batch_op.drop_constraint("uq_ingredient_lang", type_="unique")


def downgrade() -> None:
    with op.batch_alter_table("ingredient_translations") as batch_op:
        batch_op.create_unique_constraint(
            "uq_ingredient_lang", ["ingredient_id", "lang_code"]
        )
    op.drop_index(
        op.f("ix_ingredient_translations_id"),
        table_name="ingredient_translations",
    )