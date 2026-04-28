"""Интеграционные тесты для /api/v1/auth (me, register, login)."""
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------

async def test_get_me_returns_user_data(client, test_user):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == test_user.db_user.email
    assert data["username"] == test_user.db_user.username
    assert data["tenant_id"] == str(test_user.db_user.tenant_id)


async def test_get_me_unauthenticated_returns_401(unauth_client):
    r = await unauth_client.get("/api/v1/auth/me")
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------

_KC_USER_ID = str(uuid4())


async def test_register_creates_user_and_tenant(client, db_session):
    with patch(
        "api.services.user_registration_service.create_keycloak_user",
        new=AsyncMock(return_value=_KC_USER_ID),
    ):
        r = await client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "secret123",
        })
    assert r.status_code == 200
    body = r.json()
    assert body["keycloak_user_id"] == _KC_USER_ID
    assert "app_user_id" in body
    assert "tenant_id" in body


async def test_register_duplicate_email_returns_409(client, db_session):
    with patch(
        "api.services.user_registration_service.create_keycloak_user",
        new=AsyncMock(return_value=str(uuid4())),
    ):
        await client.post("/api/v1/auth/register", json={
            "username": "user1",
            "email": "dup@example.com",
            "password": "secret123",
        })
        r = await client.post("/api/v1/auth/register", json={
            "username": "user2",
            "email": "dup@example.com",
            "password": "secret123",
        })
    assert r.status_code == 409


async def test_register_username_too_long_returns_422(client):
    r = await client.post("/api/v1/auth/register", json={
        "username": "x" * 256,
        "email": "valid@example.com",
        "password": "secret123",
    })
    assert r.status_code == 422


async def test_register_password_too_short_returns_422(client):
    r = await client.post("/api/v1/auth/register", json={
        "username": "user",
        "email": "valid2@example.com",
        "password": "123",
    })
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------

async def test_login_returns_tokens(client):
    fake_response = {
        "access_token": "fake-access",
        "refresh_token": "fake-refresh",
        "token_type": "bearer",
        "expires_in": 300,
    }
    with patch(
        "api.routers.v1.auth.login_with_password",
        new=AsyncMock(return_value=fake_response),
    ):
        r = await client.post("/api/v1/auth/login", json={
            "username": "user@example.com",
            "password": "secret123",
        })
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] == "fake-access"
    assert body["token_type"] == "bearer"


async def test_login_wrong_credentials_returns_401(client):
    from fastapi import HTTPException, status as http_status

    with patch(
        "api.routers.v1.auth.login_with_password",
        new=AsyncMock(side_effect=HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин/пароль",
        )),
    ):
        r = await client.post("/api/v1/auth/login", json={
            "username": "user@example.com",
            "password": "wrongpass",
        })
    assert r.status_code == 401
