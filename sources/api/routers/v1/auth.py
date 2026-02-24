from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.deps import CurrentUser, get_current_user
from api.data_base.base import get_db_session
from api.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse
from api.services.auth_service import login_with_password
from api.services.user_registration_service import register_user as register_user_service

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@auth_router.get("/me", summary="Текущий пользователь")
async def get_me(current_user: CurrentUser = Depends(get_current_user)):
    """
    Возвращает данные пользователя и роли из токена.
    Полезно для проверки, что авторизация работает корректно.
    """
    return current_user.to_dict()


@auth_router.post("/register", summary="Самостоятельная регистрация", response_model=RegisterResponse)
async def register_user(payload: RegisterRequest, session: AsyncSession = Depends(get_db_session)):
    """
    Регистрация без авторизации:
    1) Создаем пользователя в Keycloak (через admin API).
    2) Создаем tenant в локальной БД.
    3) Создаем AppUser в локальной БД.

    Важно: email должен быть уникальным.
    """
    result = await register_user_service(
        session=session,
        username=payload.username,
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        tenant_name=payload.tenant_name,
    )
    return RegisterResponse(**result)


@auth_router.post("/login", summary="Авторизация", response_model=LoginResponse)
async def login_user(payload: LoginRequest):
    """
    Авторизация через Keycloak (password grant).
    Возвращает access_token и refresh_token.
    """
    result = await login_with_password(payload.username, payload.password)
    return LoginResponse(
        access_token=result.get("access_token", ""),
        refresh_token=result.get("refresh_token"),
        token_type=result.get("token_type", "bearer"),
        expires_in=int(result.get("expires_in", 0)),
    )
