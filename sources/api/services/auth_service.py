from __future__ import annotations

"""
Сервис авторизации через Keycloak (password grant).
Используется фронтендом для входа без ручной вставки токена.
"""

from typing import Any

import httpx
from fastapi import HTTPException, status

from settings import config


async def login_with_password(username: str, password: str) -> dict[str, Any]:
    """
    Получаем access token через Keycloak token endpoint.

    Важно: для client типа public можно обойтись без client_secret,
    для confidential — передаём client_secret.
    """
    data = {
        "grant_type": "password",
        "client_id": config.keycloak.client_id,
        "username": username,
        "password": password,
        "scope": "openid profile email",
    }

    if config.keycloak.client_secret:
        data["client_secret"] = config.keycloak.client_secret

    async with httpx.AsyncClient() as client:
        response = await client.post(config.keycloak.token_url_final, data=data, timeout=10)
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Keycloak login failed: {response.text}",
            )
        return response.json()
