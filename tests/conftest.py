"""Фикстуры для интеграционных тестов API.

Поднимаем отдельную БД `rockfile_test`, мокаем Keycloak-авторизацию
через dependency_overrides и даём клиент httpx через ASGITransport.
"""
import os
import sys
from pathlib import Path
from uuid import uuid4

# Подменяем имя БД до импорта settings.
os.environ["DATABASE__DB_NAME"] = os.environ.get("TEST_DB_NAME", "rockfile_test")

# Путь к исходникам для импортов вида `from api...`.
sources_path = Path(__file__).resolve().parent.parent / "sources"
if str(sources_path) not in sys.path:
    sys.path.insert(0, str(sources_path))

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from settings import config  # noqa: E402
from api.data_base.base import db, get_db_session  # noqa: E402
from api.data_base.models import AppUser, Base, Tenant  # noqa: E402
from api.auth.deps import CurrentUser, get_current_user  # noqa: E402
from api.auth.keycloak_module import TokenPayload  # noqa: E402
from utils.search_bootstrap import ensure_fulltext_search  # noqa: E402


async def _ensure_test_db_exists() -> None:
    """Создаём rockfile_test, если её ещё нет."""
    admin_url = (
        f"{config.database.db_driver}://"
        f"{config.database.db_user}:{config.database.db_password.get_secret_value()}@"
        f"{config.database.db_host}:{config.database.db_port}/postgres"
    )
    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as conn:
            existing = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": config.database.db_name},
            )
            if existing.scalar() is None:
                await conn.execute(text(f'CREATE DATABASE "{config.database.db_name}"'))
    finally:
        await admin_engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def _prepared_db():
    """Разово создаём тестовую БД и таблицы на всю сессию pytest."""
    await _ensure_test_db_exists()
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await ensure_fulltext_search(db.engine)
    yield
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await db.engine.dispose()


@pytest_asyncio.fixture
async def db_session(_prepared_db):
    """Чистая сессия на каждый тест — перед тестом все таблицы TRUNCATE."""
    async with db.engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE contact_links, contact_interactions, "
                "contact_family_members, contact_cards, app_users, tenants "
                "RESTART IDENTITY CASCADE"
            )
        )
    async with db.session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db_session) -> CurrentUser:
    """Создаём тестового пользователя с тенантом; возвращаем готовый CurrentUser."""
    tenant = Tenant(id=uuid4(), name=f"test-tenant-{uuid4().hex[:8]}")
    db_session.add(tenant)
    await db_session.flush()

    user = AppUser(
        id=uuid4(),
        keycloak_sub=f"test-sub-{uuid4().hex[:12]}",
        username="tester",
        email=f"tester-{uuid4().hex[:8]}@example.com",
        tenant_id=tenant.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = TokenPayload(sub=user.keycloak_sub, preferred_username=user.username, email=user.email)
    return CurrentUser(token=token, db_user=user)


def _build_app():
    """Собираем FastAPI-приложение без запуска lifespan (миграции и логи не нужны в тестах)."""
    from fastapi import FastAPI
    from api.routers.v1.auth import auth_router
    from api.routers.v1.contacts import contacts_router
    from api.routers.v1.contact_links import contact_links_router
    from api.routers.v1.contact_interactions import contact_interactions_router
    from api.routers.v1.search import search_router
    from api.routers.v1.promises import promises_router

    # Переиспользуем те же exception handlers, что и в проде.
    from api.fastapi_app import (
        http_exception_handler,
        validation_exception_handler,
        generic_exception_handler,
    )
    from fastapi import HTTPException
    from fastapi.exceptions import RequestValidationError

    app = FastAPI(title="Rockfile-tests")
    app.include_router(auth_router)
    app.include_router(contacts_router)
    app.include_router(contact_links_router)
    app.include_router(contact_interactions_router)
    app.include_router(search_router)
    app.include_router(promises_router)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    return app


@pytest_asyncio.fixture
async def client(test_user):
    """HTTPX клиент: подменяем auth и сессию БД."""
    app = _build_app()

    async def _override_user():
        return test_user

    async def _override_session():
        async with db.session_factory() as session:
            yield session

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db_session] = _override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def unauth_client():
    """Клиент без override авторизации — для проверки 401."""
    app = _build_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
