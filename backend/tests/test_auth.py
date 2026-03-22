"""Tests for /auth endpoints."""
import pytest


@pytest.mark.asyncio
async def test_login_success(client):
    resp = await client.post("/auth/login", json={"username": "jinhoadmin", "password": "superpass"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    resp = await client.post("/auth/login", json={"username": "jinhoadmin", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client):
    resp = await client.post("/auth/login", json={"username": "nobody", "password": "x"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me(client, admin_token):
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "jinhoadmin"


@pytest.mark.asyncio
async def test_me_no_token(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_must_change_password_flag(client):
    """admin user must have must_change_password=True on login."""
    resp = await client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200
    assert resp.json()["must_change_password"] is True


@pytest.mark.asyncio
async def test_change_password(client, admin_token):
    resp = await client.post(
        "/auth/change-password",
        json={"current_password": "superpass", "new_password": "newpass123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    # Old password should now fail
    resp2 = await client.post("/auth/login", json={"username": "jinhoadmin", "password": "superpass"})
    assert resp2.status_code == 401

    # New password should work
    resp3 = await client.post("/auth/login", json={"username": "jinhoadmin", "password": "newpass123"})
    assert resp3.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current(client, admin_token):
    resp = await client.post(
        "/auth/change-password",
        json={"current_password": "wrongpass", "new_password": "newpass123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
