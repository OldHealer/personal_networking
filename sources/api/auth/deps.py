from typing import Any

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2AuthorizationCodeBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.keycloak_module import TokenPayload, verify_jwt_token
from api.data_base.base import get_db_session
from api.data_base.models import AppUser
from settings import config

# OAuth2 Authorization Code flow для Swagger UI
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=config.keycloak.auth_url_final,
    tokenUrl=config.keycloak.token_url_final,
    scopes={},
)


class CurrentUser:
    """Объект, который возвращаем в зависимости для роутов."""

    def __init__(self, token: TokenPayload, db_user: AppUser):
        self.token = token
        self.db_user = db_user

    def to_dict(self) -> dict[str, Any]:
        """Удобный сериализатор для отладки."""
        return {
            "id": str(self.db_user.id),
            "keycloak_sub": self.db_user.keycloak_sub,
            "username": self.db_user.username,
            "email": self.db_user.email,
            "tenant_id": str(self.db_user.tenant_id) if self.db_user.tenant_id else None,
            "roles": self.token.roles,
        }


async def _get_or_create_user(session: AsyncSession, token: TokenPayload) -> AppUser:
    """Создаём пользователя в БД при первом входе."""
    query = select(AppUser).where(AppUser.keycloak_sub == token.sub)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    if user:
        return user

    # Создаём нового пользователя из токена
    user = AppUser(
        keycloak_sub=token.sub,
        username=token.preferred_username,
        email=token.email,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_current_user(
    token_str: str = Security(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> CurrentUser:
    """
    Dependency:
    1) Проверяем наличие Bearer токена
    2) Валидируем JWT (подпись/iss/aud/exp)
    3) Создаём пользователя в БД при первом входе
    """
    token_payload = await verify_jwt_token(token_str)
    db_user = await _get_or_create_user(session, token_payload)
    return CurrentUser(token=token_payload, db_user=db_user)
