"""Seed initial users into the database.

Reads env vars for credentials; dev defaults are used if not set.
Run after Alembic migration 0010:
    python seed.py

Env vars:
    SEED_ADMIN_USERNAME   (default: admin)
    SEED_ADMIN_PASSWORD   (default: admin123)
    SEED_USER1_USERNAME   (default: lurio)
    SEED_USER1_PASSWORD   (default: lurio123)
    SEED_USER2_USERNAME   (default: nursek)
    SEED_USER2_PASSWORD   (default: nursek123)
"""

from __future__ import annotations

import asyncio
import os

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.services.auth import hash_password


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


USERS_TO_SEED = [
    {
        "username": _env("SEED_ADMIN_USERNAME", "admin"),
        "password": _env("SEED_ADMIN_PASSWORD", "admin123"),
        "role": "admin",
    },
    {
        "username": _env("SEED_USER1_USERNAME", "lurio"),
        "password": _env("SEED_USER1_PASSWORD", "lurio123"),
        "role": "user",
    },
    {
        "username": _env("SEED_USER2_USERNAME", "nursek"),
        "password": _env("SEED_USER2_PASSWORD", "nursek123"),
        "role": "user",
    },
]


async def seed() -> None:
    async with SessionLocal() as db:
        for spec in USERS_TO_SEED:
            username = spec["username"]
            password = spec["password"]
            role = spec["role"]
            hashed = hash_password(password)

            existing = await db.scalar(select(User).where(User.username == username))
            if existing:
                print(f"Skipped (already exists): {username}")
            else:
                db.add(User(username=username, hashed_password=hashed, role=role))
                print(f"Created user: {username} (role={role})")

        await db.commit()
    print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
