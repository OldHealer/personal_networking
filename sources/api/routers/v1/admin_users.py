"""
Роуты для администратора:
- создание пользователя в Keycloak
- синхронизация пользователя в локальной БД
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.deps import CurrentUser, require_superadmin
from api.data_base.base import get_db_session
from api.schemas.admin_users import AdminCreateUserRequest, AdminCreateUserResponse
from api.services.user_registration_service import admin_create_user

admin_users_router = APIRouter(prefix="/api/v1/admin/users", tags=["Admin"])


@admin_users_router.post("/", summary="Создать пользователя (Keycloak + БД)", response_model=AdminCreateUserResponse)
async def admin_create_user(payload: AdminCreateUserRequest, 
                            _: CurrentUser = Depends(require_superadmin), 
                            session: AsyncSession = Depends(get_db_session)):
    """
    1) Создаём пользователя в Keycloak
    2) Создаём tenant в БД
    3) Создаём AppUser в БД и связываем с tenant
    """
    result = await admin_create_user(session=session,
                                     username=payload.username,
                                     email=payload.email,
                                     password=payload.password,
                                     tenant_name=payload.tenant_name)
    return AdminCreateUserResponse(**result)
