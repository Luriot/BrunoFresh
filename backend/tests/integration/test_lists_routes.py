"""Integration tests for the /api/lists/* endpoints."""
from __future__ import annotations

import pytest

from app.models import ShoppingList, ShoppingListItem, User


async def test_list_display_name_fr(anon_client, db_session):
    """With a 'fr' token, shopping list item display_name uses name_fr when available."""
    from app.config import settings
    from app.services.auth import hash_password, issue_access_token

    fr_user = User(username="_fr_list_test_", hashed_password=hash_password("_"), role="user", language="fr")
    db_session.add(fr_user)
    await db_session.commit()
    await db_session.refresh(fr_user)

    shopping_list = ShoppingList(user_id=fr_user.id, label="FR test list")
    db_session.add(shopping_list)
    await db_session.commit()
    await db_session.refresh(shopping_list)

    item = ShoppingListItem(
        shopping_list_id=shopping_list.id,
        name="milk",
        name_fr="lait",
        quantity=1.0,
        unit="L",
        category="Dairy",
    )
    db_session.add(item)
    await db_session.commit()

    token = issue_access_token(fr_user.id, "user", "fr")
    resp = await anon_client.get(
        f"/api/lists/{shopping_list.id}", cookies={settings.auth_cookie_name: token}
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["display_name"] == "lait"


async def test_list_display_name_fr_fallback(anon_client, db_session):
    """With a 'fr' token but no name_fr, display_name falls back to name_en."""
    from app.config import settings
    from app.services.auth import hash_password, issue_access_token

    fr_user = User(username="_fr_list_fallback_", hashed_password=hash_password("_"), role="user", language="fr")
    db_session.add(fr_user)
    await db_session.commit()
    await db_session.refresh(fr_user)

    shopping_list = ShoppingList(user_id=fr_user.id, label="FR fallback list")
    db_session.add(shopping_list)
    await db_session.commit()
    await db_session.refresh(shopping_list)

    item = ShoppingListItem(
        shopping_list_id=shopping_list.id,
        name="milk",
        name_fr=None,
        quantity=1.0,
        unit="L",
        category="Dairy",
    )
    db_session.add(item)
    await db_session.commit()

    token = issue_access_token(fr_user.id, "user", "fr")
    resp = await anon_client.get(
        f"/api/lists/{shopping_list.id}", cookies={settings.auth_cookie_name: token}
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["display_name"] == "milk"
