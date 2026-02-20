from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.deps import CurrentUser, get_current_user
from api.data_base.base import get_db_session
from api.schemas.auth import RegisterRequest, RegisterResponse
from api.services.user_registration_service import register_user  as register_user_service

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
    result = await register_user_service(session=session,
                                         username=payload.username,
                                         email=payload.email,
                                         password=payload.password,
                                         tenant_name=payload.tenant_name)
    return RegisterResponse(**result)
