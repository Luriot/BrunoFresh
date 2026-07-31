"""Seed initial users into the database.

Requires explicit credentials via env vars (no committed defaults). Run after
Alembic migration 0010:

    SEED_ADMIN_PASSWORD=... SEED_USER1_PASSWORD=... SEED_USER2_PASSWORD=... python seed.py

Optional overrides:
    SEED_ADMIN_USERNAME   (default: admin)
    SEED_USER1_USERNAME    (default: lurio)
    SEED_USER2_USERNAME    (default: nursek)
"""

from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import User
from app.services.auth import hash_password


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _required_password_env(var_name: str) -> str:
    val = os.environ.get(var_name)
    if not val or not val.strip():
        print(
            f"ERROR: {var_name} must be set to a strong password before seeding. "
            "Committed default credentials are not allowed.",
            file=sys.stderr,
        )
        sys.exit(1)
    return val.strip()


USERS_TO_SEED = [
    {
        "username": _env("SEED_ADMIN_USERNAME", "admin"),
        "password_env": "SEED_ADMIN_PASSWORD",
        "role": "admin",
    },
    {
        "username": _env("SEED_USER1_USERNAME", "lurio"),
        "password_env": "SEED_USER1_PASSWORD",
        "role": "user",
    },
    {
        "username": _env("SEED_USER2_USERNAME", "nursek"),
        "password_env": "SEED_USER2_PASSWORD",
        "role": "user",
    },
]


async def seed() -> None:
    async with SessionLocal() as db:
        for spec in USERS_TO_SEED:
            username = spec["username"]
            role = spec["role"]

            existing = await db.scalar(select(User).where(User.username == username))
            if existing:
                print(f"Skipped (already exists): {username}")
                continue

            password = _required_password_env(spec["password_env"])
            hashed = hash_password(password)
            db.add(User(username=username, hashed_password=hashed, role=role))
            print(f"Created user: {username} (role={role})")

        await db.commit()
    print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())