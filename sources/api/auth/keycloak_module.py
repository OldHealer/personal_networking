import time
from typing import Any

import httpx
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from fastapi import HTTPException, status

from settings import config

# Простое кэширование JWKS, чтобы не дергать Keycloak на каждый запрос
_JWKS_CACHE: dict[str, Any] | None = None
_JWKS_CACHE_EXPIRES_AT: float | None = None


class TokenPayload(BaseModel):
    """Минимальный набор полей из JWT, которые нам нужны."""

    sub: str = Field(..., description="Уникальный идентификатор пользователя в Keycloak")
    preferred_username: str | None = Field(None, description="Имя пользователя")
    email: str | None = Field(None, description="Email пользователя")
    tenant_id: str | None = Field(None, description="ID арендатора (если добавим в claim)")
    realm_access: dict | None = Field(None, description="Роли в realm (Keycloak)")

    @property
    def roles(self) -> list[str]:
        """Удобный доступ к ролям из realm_access.roles."""
        if not self.realm_access:
            return []
        return self.realm_access.get("roles", []) or []


async def _fetch_jwks() -> dict[str, Any]:
    """Запрос JWKS (публичных ключей) у Keycloak."""
    async with httpx.AsyncClient() as client:
        response = await client.get(config.keycloak.jwks_url_final, timeout=10)
        response.raise_for_status()
        return response.json()


async def _get_jwks_cached() -> dict[str, Any]:
    """Кэшируем JWKS на 5 минут для экономии запросов."""
    global _JWKS_CACHE, _JWKS_CACHE_EXPIRES_AT

    now = time.time()
    if _JWKS_CACHE and _JWKS_CACHE_EXPIRES_AT and now < _JWKS_CACHE_EXPIRES_AT:
        return _JWKS_CACHE

    _JWKS_CACHE = await _fetch_jwks()
    _JWKS_CACHE_EXPIRES_AT = now + 300  # 5 минут
    return _JWKS_CACHE


def _select_jwk(jwks: dict, kid: str) -> dict | None:
    """Выбираем ключ по kid из JWKS."""
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


async def verify_jwt_token(token: str) -> TokenPayload:
    """
    Проверяем JWT:
    - подпись (по JWK)
    - issuer
    - audience
    - срок действия
    """
    try:
        # Извлекаем kid (идентификатор ключа) из заголовка токена
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing kid")

        jwks = await _get_jwks_cached()
        jwk = _select_jwk(jwks, kid)
        if not jwk:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown kid in token")

        # Декодируем и валидируем токен
        payload = jwt.decode(
            token,
            jwk,
            algorithms=[jwk.get("alg", "RS256")],
            audience=config.keycloak.audience,
            issuer=config.keycloak.issuer,
            options={
                "verify_aud": True,
                "verify_iss": True,
                "verify_exp": True,
            },
        )

        return TokenPayload(**payload)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc
