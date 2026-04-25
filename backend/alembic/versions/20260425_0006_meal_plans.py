"""add meal_plans and meal_plan_entries tables

Revision ID: 20260425_0006
Revises: 20260425_0005
Create Date: 2026-04-25 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260425_0006"
down_revision: Union[str, Sequence[str], None] = "20260425_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "meal_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=True),
        sa.Column("week_start_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_meal_plans_id"), "meal_plans", ["id"], unique=False)

    op.create_table(
        "meal_plan_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("meal_plan_id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("meal_slot", sa.String(length=40), nullable=True),
        sa.Column("target_servings", sa.Integer(), nullable=False, server_default="2"),
        sa.ForeignKeyConstraint(["meal_plan_id"], ["meal_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_meal_plan_entries_id"), "meal_plan_entries", ["id"], unique=False)
    op.create_index(op.f("ix_meal_plan_entries_meal_plan_id"), "meal_plan_entries", ["meal_plan_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_meal_plan_entries_meal_plan_id"), table_name="meal_plan_entries")
    op.drop_index(op.f("ix_meal_plan_entries_id"), table_name="meal_plan_entries")
    op.drop_table("meal_plan_entries")
    op.drop_index(op.f("ix_meal_plans_id"), table_name="meal_plans")
    op.drop_table("meal_plans")
