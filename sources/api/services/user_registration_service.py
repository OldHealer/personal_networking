""" Сервис регистрации пользователей и создания tenant """

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.keycloak_admin import create_keycloak_user
from api.data_base.models import AppUser, Tenant


async def _ensure_unique_email(session: AsyncSession, email: str) -> None:
    """Проверяем, что email не занят в локальной БД."""

    existing_query = select(AppUser).where(AppUser.email == email)
    existing_result = await session.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")


async def _generate_unique_tenant_name(session: AsyncSession, base_name: str) -> str:
    """
    Генерируем уникальное имя tenant.
    Если имя уже занято, добавляем суффикс -2, -3, ...
    """
    candidate_name = base_name
    suffix = 1

    while True:
        tenant_query = select(Tenant).where(Tenant.name == candidate_name)
        tenant_result = await session.execute(tenant_query)
        if not tenant_result.scalar_one_or_none():
            return candidate_name
        suffix += 1
        candidate_name = f"{base_name}-{suffix}"


def _build_keycloak_payload(username: str, email: str, password: str) -> dict:
    """Формируем payload для создания пользователя в Keycloak."""

    return {
        "username": username,
        "email": email,
        "enabled": True,
        "emailVerified": True,
        "credentials": [
            {
                "type": "password",
                "value": password,
                "temporary": False,
            }
        ],
    }


async def register_user(session: AsyncSession,
                        username: str,
                        email: str,
                        password: str,
                        tenant_name: str | None) -> dict:
    """
    Самостоятельная регистрация:
    1) Проверяем уникальность email в БД
    2) Создаем пользователя в Keycloak
    3) Создаем tenant
    4) Создаем AppUser в БД
    """
    # есть ли такой пользователь
    await _ensure_unique_email(session, email)
    # сформируй уникальный tenant
    base_name = tenant_name or username or email
    candidate_name = await _generate_unique_tenant_name(session, base_name)

    # 1) Пользователь в Keycloak
    payload = _build_keycloak_payload(username, email, password)
    keycloak_user_id = await create_keycloak_user(payload)

    # 2) Tenant в БД
    tenant = Tenant(name=candidate_name)
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)

    # 3) Пользователь в БД
    user = AppUser(keycloak_sub=keycloak_user_id, username=username, email=email, tenant_id=tenant.id)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return {"keycloak_user_id": keycloak_user_id,
            "app_user_id": str(user.id),
            "tenant_id": str(tenant.id)}


async def admin_create_user(session: AsyncSession,
                            username: str,
                            email: str,
                            password: str,
                            tenant_name: str) -> dict:
    """
    Регистрация пользователя администратором:
    1) Проверяем уникальность email в БД
    2) Создаем пользователя в Keycloak
    3) Создаем tenant
    4) Создаем AppUser в БД
    """
    await _ensure_unique_email(session, email)

    # Админ сам задает имя tenant, но проверяем уникальность и
    # при необходимости добавляем суффикс.
    candidate_name = await _generate_unique_tenant_name(session, tenant_name)

    payload = _build_keycloak_payload(username, email, password)
    keycloak_user_id = await create_keycloak_user(payload)

    tenant = Tenant(name=candidate_name)
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)

    user = AppUser(keycloak_sub=keycloak_user_id,
                   username=username,
                   email=email,
                   tenant_id=tenant.id)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return {"keycloak_user_id": keycloak_user_id,
            "app_user_id": str(user.id),
            "tenant_id": str(tenant.id)}
