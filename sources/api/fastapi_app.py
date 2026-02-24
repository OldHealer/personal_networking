import asyncio
import json
import logging
import os
import traceback

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, Response
# from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
# from fastapi.exceptions import RequestValidationError, HTTPException
from pydantic import BaseModel, Field

from api.data_base.models import Base
from api.routers.v1.auth import auth_router
from api.data_base.base import db
from utils.db_bootstrap import ensure_database_exists, run_migrations
from settings import config

# setup_audit_logger_loguru(json_format=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    События на протяжении жизни сервиса

    :param app: FastAPI - приложение
    :return:
    """
    try:
        existed = await ensure_database_exists()
        alembic_ini_path = Path(config.alembic_path)
        if alembic_ini_path.exists():
            if existed:
                print("БД существует. Применяю миграции...")
            else:
                print("БД отсутствовала. Создал БД и применяю миграции...")
            run_migrations()
        else:
            # Если миграций нет, создаем таблицы напрямую
            print("Alembic не настроен. Создаю таблицы через SQLAlchemy.")
            await db.init_models(base=Base)
        # Инициализируем базу данных, если её нет - она будет создана со всеми таблицами
        # if await db.check_connection():
        #     print('Соединение с БД установлено, произвожу инициализацию таблиц')
        #     await db.init_models(base=Base)

        # logger.info('Проверяю наличие новых миграций')
        # success = await check_and_upgrade(db)
        # logger.info(f'Статус проверок и обновлений миграций: {success}')
        # if not success:
        #     raise RuntimeError("Миграции не удалось применить")

        print(f'Приложение персонального нетворкинга запущено')

        # Регистрируем маршруты
        # app.include_router(llm_public_router, prefix="/api/v1")
        # app.include_router(plugin_public_router, prefix="/api/v1")
        # app.include_router(llm_admin_router, prefix="/api/v1")
        # app.include_router(plugin_admin_router, prefix="/api/v1")
        # app.include_router(user_groups_router, prefix="/api/v1")
        # app.include_router(sources_router, prefix="/api/v1")
        # app.include_router(users_admin_router, prefix="/api/v1")
        # app.include_router(worker_router, prefix="/api/v1")
        # app.include_router(cluster_worker_router, prefix="/api/v1")
        # app.include_router(llm_instance_router, prefix="/api/v1")
        # app.include_router(auth_router, prefix="/api/v1")
        # app.include_router(tokens_admin_router, prefix="/api/v1")
        # app.include_router(tokens_public_router, prefix="/api/v1")

        # Передача управления FastAPI
        yield



    except Exception as e:
        print(f'Ошибка: {e}')
    finally:
        print(f'Приложение остановлено')

app = FastAPI(
    title="Rockfile",
    description="API персональной картотеки и нетворкинга.",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",  # Путь к JSON-схеме OpenAPI
    redoc_url="/api/redoc",
    swagger_ui_init_oauth={
        "clientId": config.keycloak.client_id,
        "usePkceWithAuthorizationCodeGrant": True,
    },
    lifespan=lifespan,  # Use the lifespan manager
)


BASE_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = BASE_DIR / "web"
ASSETS_DIR = WEB_DIR / "assets"

# Статика фронтенда
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/web", summary="Фронтенд: главная страница", include_in_schema=False)
async def web_index():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/index.html", summary="Фронтенд: главная страница (html)", include_in_schema=False)
async def web_index_html():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/login", summary="Фронтенд: авторизация", include_in_schema=False)
async def web_login():
    return FileResponse(WEB_DIR / "login.html")


@app.get("/login.html", summary="Фронтенд: авторизация (html)", include_in_schema=False)
async def web_login_html():
    return FileResponse(WEB_DIR / "login.html")


@app.get("/success", summary="Фронтенд: успешная авторизация", include_in_schema=False)
async def web_success():
    return FileResponse(WEB_DIR / "success.html")


@app.get("/success.html", summary="Фронтенд: успешная авторизация (html)", include_in_schema=False)
async def web_success_html():
    return FileResponse(WEB_DIR / "success.html")


@app.get("/error", summary="Фронтенд: ошибка авторизации", include_in_schema=False)
async def web_error():
    return FileResponse(WEB_DIR / "error.html")


@app.get("/error.html", summary="Фронтенд: ошибка авторизации (html)", include_in_schema=False)
async def web_error_html():
    return FileResponse(WEB_DIR / "error.html")



@app.get("/", summary="Корневой эндпоинт")
async def root_index():
    return {
        "message": "API запущено. Откройте /api/docs для Swagger.",
        "docs": "/api/docs",
    }


router = APIRouter(prefix="/api/v1", tags=["Базовые"])


@router.get("/ping", summary="Проверка доступности")
async def ping():
    return {"status": "ok"}


@router.get("/", summary="Корневой эндпоинт v1")
async def root():
    return {
        "name": app.title,
        "description": app.description,
        "version": app.version,
    }


app.include_router(router)
app.include_router(auth_router)

