"""Add language column to users table

Revision ID: 20260516_0011
Revises: 20260512_0010_user_avatar
Create Date: 2026-05-16
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260516_0011"
down_revision = "20260512_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("language", sa.String(10), nullable=False, server_default="'en'"),
    )


def downgrade() -> None:
    op.drop_column("users", "language")
