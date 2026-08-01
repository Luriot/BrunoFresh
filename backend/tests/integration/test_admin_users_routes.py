"""Integration tests for admin user-management endpoints under /api/admin/users."""
from __future__ import annotations

import pytest

from app.models import User
from app.services.auth import hash_password, verify_password


async def _make_user(db_session, username: str, role: str = "user") -> User:
    u = User(username=username, hashed_password=hash_password("initial123"), role=role)
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


# ── GET /api/admin/users ──────────────────────────────────────────────────────

async def test_admin_list_users(admin_client, db_session):
    await _make_user(db_session, "alice")
    res = await admin_client.get("/api/admin/users")
    assert res.status_code == 200
    names = [u["username"] for u in res.json()]
    assert "alice" in names and "_admin_stub_" in names


async def test_non_admin_cannot_list_users(client):
    res = await client.get("/api/admin/users")
    assert res.status_code == 403


# ── PATCH /api/admin/users/{id} (role) ────────────────────────────────────────

async def test_admin_promote_user_to_admin(admin_client, db_session):
    u = await _make_user(db_session, "bob")
    res = await admin_client.patch(f"/api/admin/users/{u.id}", json={"role": "admin"})
    assert res.status_code == 200
    assert res.json()["role"] == "admin"


async def test_admin_cannot_change_own_role(admin_client, db_session):
    from sqlalchemy import select
    me = (await db_session.execute(select(User).where(User.username == "_admin_stub_"))).scalar_one()
    res = await admin_client.patch(f"/api/admin/users/{me.id}", json={"role": "user"})
    assert res.status_code == 400


async def test_invalid_role_rejected(admin_client, db_session):
    u = await _make_user(db_session, "dave")
    res = await admin_client.patch(f"/api/admin/users/{u.id}", json={"role": "superuser"})
    assert res.status_code == 422


# ── POST /api/admin/users/{id}/reset-password ─────────────────────────────────

async def test_admin_reset_password_works(admin_client, db_session):
    u = await _make_user(db_session, "erin")
    res = await admin_client.post(f"/api/admin/users/{u.id}/reset-password", json={"new_password": "newpass123"})
    assert res.status_code == 200
    await db_session.refresh(u)
    assert verify_password("newpass123", u.hashed_password)
    assert not verify_password("initial123", u.hashed_password)


async def test_short_password_rejected(admin_client, db_session):
    u = await _make_user(db_session, "frank")
    res = await admin_client.post(f"/api/admin/users/{u.id}/reset-password", json={"new_password": "short"})
    assert res.status_code == 422


async def test_admin_cannot_reset_own_password(admin_client, db_session):
    from sqlalchemy import select
    me = (await db_session.execute(select(User).where(User.username == "_admin_stub_"))).scalar_one()
    res = await admin_client.post(f"/api/admin/users/{me.id}/reset-password", json={"new_password": "newpass123"})
    assert res.status_code == 400


async def test_reset_unknown_user_404(admin_client):
    res = await admin_client.post("/api/admin/users/9999/reset-password", json={"new_password": "newpass123"})
    assert res.status_code == 404