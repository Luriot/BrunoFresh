"""Add nutrition columns to recipes table

Revision ID: 20260603_0012
Revises: 20260516_0011
Create Date: 2026-06-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260603_0012"
down_revision = "20260516_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("recipes", sa.Column("kcal", sa.Integer(), nullable=True))
    op.add_column("recipes", sa.Column("protein_g", sa.Integer(), nullable=True))
    op.add_column("recipes", sa.Column("carbs_g", sa.Integer(), nullable=True))
    op.add_column("recipes", sa.Column("fat_g", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("recipes", "fat_g")
    op.drop_column("recipes", "carbs_g")
    op.drop_column("recipes", "protein_g")
    op.drop_column("recipes", "kcal")