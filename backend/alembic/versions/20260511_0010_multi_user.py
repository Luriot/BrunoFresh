"""multi-user accounts, per-user favorites, per-user data

Revision ID: 20260511_0010
Revises: 20260429_0009
Create Date: 2026-05-11 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260511_0010"
down_revision: Union[str, None] = "20260429_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(80), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(200), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # 2. Insert a placeholder admin user (seed.py will set the real password)
    op.execute(
        "INSERT INTO users (username, hashed_password, role) VALUES ('admin', '$PLACEHOLDER$', 'admin')"
    )

    # 3. Create user_favorites table
    op.create_table(
        "user_favorites",
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "recipe_id",
            sa.Integer,
            sa.ForeignKey("recipes.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_user_favorites_recipe_id", "user_favorites", ["recipe_id"])

    # 4. Migrate is_favorite=True recipes to admin's favorites
    op.execute(
        "INSERT INTO user_favorites (user_id, recipe_id) "
        "SELECT (SELECT id FROM users WHERE username='admin'), id "
        "FROM recipes WHERE is_favorite = 1"
    )

    # 5. Add nullable user_id FK to shopping_lists and migrate existing rows
    with op.batch_alter_table("shopping_lists") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer, nullable=True))
        batch_op.create_index("ix_shopping_lists_user_id", ["user_id"])
        batch_op.create_foreign_key(
            "fk_shopping_lists_user_id", "users", ["user_id"], ["id"], ondelete="SET NULL"
        )
    op.execute(
        "UPDATE shopping_lists SET user_id = (SELECT id FROM users WHERE username='admin') "
        "WHERE user_id IS NULL"
    )

    # 6. Add nullable user_id FK to pantry_items and migrate existing rows
    with op.batch_alter_table("pantry_items") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer, nullable=True))
        batch_op.create_index("ix_pantry_items_user_id", ["user_id"])
        batch_op.create_foreign_key(
            "fk_pantry_items_user_id", "users", ["user_id"], ["id"], ondelete="SET NULL"
        )
    op.execute(
        "UPDATE pantry_items SET user_id = (SELECT id FROM users WHERE username='admin') "
        "WHERE user_id IS NULL"
    )

    # 7. Add nullable user_id FK to meal_plans and migrate existing rows
    with op.batch_alter_table("meal_plans") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer, nullable=True))
        batch_op.create_index("ix_meal_plans_user_id", ["user_id"])
        batch_op.create_foreign_key(
            "fk_meal_plans_user_id", "users", ["user_id"], ["id"], ondelete="SET NULL"
        )
    op.execute(
        "UPDATE meal_plans SET user_id = (SELECT id FROM users WHERE username='admin') "
        "WHERE user_id IS NULL"
    )

    # 8. Drop is_favorite from recipes (data already migrated above)
    with op.batch_alter_table("recipes") as batch_op:
        batch_op.drop_column("is_favorite")


def downgrade() -> None:
    # Restore is_favorite on recipes
    op.add_column(
        "recipes",
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # Remove user_id columns
    with op.batch_alter_table("meal_plans") as batch_op:
        batch_op.drop_column("user_id")

    with op.batch_alter_table("pantry_items") as batch_op:
        batch_op.drop_column("user_id")

    with op.batch_alter_table("shopping_lists") as batch_op:
        batch_op.drop_column("user_id")

    op.drop_table("user_favorites")
    op.drop_table("users")
