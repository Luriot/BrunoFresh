"""Integration tests: GET /api/health — no auth required."""
import pytest


async def test_health_returns_ok(anon_client):
    response = await anon_client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_does_not_require_auth(anon_client):
    """Health endpoint must be reachable without a session cookie."""
    response = await anon_client.get("/api/health")
    assert response.status_code == 200
