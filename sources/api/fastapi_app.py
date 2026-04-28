import asyncio
import json
import logging
import os
import traceback

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, APIRouter
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response
from fastapi import HTTPException
from pydantic import BaseModel, Field

from api.data_base.models import Base
from api.routers.v1.auth import auth_router
from api.routers.v1.agents import agents_router
from api.routers.v1.contacts import contacts_router
from api.routers.v1.contact_links import contact_links_router
from api.routers.v1.contact_interactions import contact_interactions_router
from api.routers.v1.search import search_router
from api.data_base.base import db
from utils.db_bootstrap import ensure_database_exists, run_migrations
from utils.search_bootstrap import ensure_fulltext_search
from settings import config

from utils.logger_loguru import setup_audit_logger_loguru, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    События на протяжении жизни сервиса

    :param app: FastAPI - приложение
    :return:
    """
    try:
        # Инициализация логгера
        setup_audit_logger_loguru(to_file=True, json_format=False, log_level="INFO")
        log = get_logger()

        existed = await ensure_database_exists()
        alembic_ini_path = Path(config.alembic_path)
        if alembic_ini_path.exists():
            if existed:
                log.info("БД существует. Применяю миграции...")
            else:
                log.info("БД отсутствовала. Создал БД и применяю миграции...")
            await run_migrations()
        else:
            # Если миграций нет, создаем таблицы напрямую
            log.info("Alembic не настроен. Создаю таблицы через SQLAlchemy.")
            await db.init_models(base=Base)

        # Полнотекстовый поиск: генерируемые tsvector-колонки + GIN-индексы (идемпотентно).
        await ensure_fulltext_search(db.engine)

        log.info(f'Приложение персонального нетворкинга запущено')

        # Регистрация маршрутов
        app.include_router(auth_router)
        app.include_router(contacts_router)
        app.include_router(contact_links_router)
        app.include_router(contact_interactions_router)
        app.include_router(search_router)
        app.include_router(agents_router)

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


# --- Единый формат ответов об ошибках (1.4.3) ---


class ErrorDetail(BaseModel):
    """Один элемент ошибки валидации (422)."""

    loc: list[str] = Field(..., description="Путь к полю (например ['body', 'full_name'])")
    msg: str = Field(..., description="Сообщение об ошибке")
    type: str | None = Field(None, description="Тип ошибки Pydantic")


class ErrorResponse(BaseModel):
    """Единый формат ответа при ошибке."""

    status_code: int = Field(..., description="HTTP-код ответа")
    detail: str | list[ErrorDetail] = Field(..., description="Описание ошибки или список ошибок валидации")
    error: str | None = Field(None, description="Код типа ошибки: validation_error, not_found, internal_error")


def _error_json_response(status_code: int, detail: str | list, error: str | None = None) -> JSONResponse:
    body = {"status_code": status_code, "detail": detail}
    if error:
        body["error"] = error
    return JSONResponse(status_code=status_code, content=body)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """404, 403, 401 и прочие HTTP-ошибки — единый формат."""
    detail = exc.detail
    if isinstance(detail, (list, dict)):
        detail = str(detail)
    error_code = "not_found" if exc.status_code == 404 else None
    return _error_json_response(exc.status_code, detail, error_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """422 — ошибки валидации (Pydantic) в едином формате."""
    details = [
        ErrorDetail(loc=[str(x) for x in err["loc"]], msg=err.get("msg", ""), type=err.get("type"))
        for err in exc.errors()
    ]
    return _error_json_response(422, [d.model_dump() for d in details], "validation_error")


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """500 — необработанные исключения, единый формат, трейсбек в лог."""
    traceback.print_exc()
    return _error_json_response(
        500,
        "Internal server error",
        "internal_error",
    )


# --- Статика и маршруты ---



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


@app.get("/contacts", summary="Фронтенд: контакты", include_in_schema=False)
async def web_contacts():
    return FileResponse(WEB_DIR / "contacts.html")

@app.get("/contacts.html", summary="Фронтенд: контакты (html)", include_in_schema=False)
async def web_contacts_html():
    return FileResponse(WEB_DIR / "contacts.html")

@app.get("/contact", summary="Фронтенд: карточка контакта", include_in_schema=False)
async def web_contact():
    return FileResponse(WEB_DIR / "contact.html")

@app.get("/contact.html", summary="Фронтенд: карточка контакта (html)", include_in_schema=False)
async def web_contact_html():
    return FileResponse(WEB_DIR / "contact.html")

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



