import asyncio
import json
import logging
import os
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, APIRouter
# from fastapi.openapi.utils import get_openapi
# from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, Response
# from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
# from fastapi.exceptions import RequestValidationError, HTTPException
from pydantic import BaseModel, Field

# from api.core.fastapi_keycloak_auth import check_keycloak_availability, delete_keycloak_session
# from api.core.minio_link_generate import check_minio_connection
# from api.core.tabby_module import check_tabby_connection
# from api.core.tabby_module_new import TabbyManager
# from api.routers.v1.admin.llm import llm_admin_router
# from api.routers.v1.admin.llm_instance import llm_instance_router, llm_instance_manager
# from api.routers.v1.admin.plugins import plugin_admin_router
# from api.routers.v1.admin.tokens import tokens_admin_router
# from api.routers.v1.admin.users import users_admin_router
# from api.routers.v1.admin.user_groups import router as user_groups_router
# from api.routers.v1.admin.sources_data import router as sources_router
# from api.routers.v1.admin.workers import worker_router
# from api.routers.v1.admin.cluster import cluster_worker_router
# from api.routers.v1.public.llm import llm_public_router
# from api.routers.v1.public.plugins import plugin_public_router
# from api.routers.v1.keycloak_auth import auth_router
# from api.routers.v1.public.tokens import tokens_public_router
# from api.schemas.general import StatusOrErrorResponse
# from erebus_db.base import db
# from erebus_db.models import Base
# from tasks.token_expiration import periodic_token_gc_worker
# from utils.async_email_sender import send_email
# from utils.alembic_runner import check_and_upgrade
# from utils.context_provider_synchonize import synchronize_sources
# from utils.logger_loguru import setup_audit_logger_loguru
# from utils.audit_logger.audit_events import log_audit_event, AuditEventType
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
    lifespan=lifespan,  # Use the lifespan manager
)

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


# @app.get("/api/v1/openapi_json", tags=["Документация"])
# async def get_openapi_json():
#     return Response(
#         content=json.dumps(app.openapi()),
#         media_type="application/json"
#     )
#
# class HealthServices(BaseModel):
#     postgres: bool = Field(default=False, title="PostgresDB", description="Соединение с базой данных")
#
# @app.get("/api/health_services", tags=["Проверка сервисов"], summary="Проверка соединения с внешними сервисами", response_model=HealthServices)
# async def get_health_services():
#     return {
#         'postgres': await db.check_connection(),
#     }
#
# class RequestAccess(BaseModel):
#     name: str
#     email: str
#     company: str
#     comment: str | None = None
#
# @app.post("/api/v1/request-access", tags=['Запрос доступа'], summary="Запрос доступа",
#           responses={200: {"description": "Успешный запрос"}, 500: {"description": "Внутренняя ошибка сервера"}},
#           response_model=StatusOrErrorResponse)
# async def post_request_access(request: RequestAccess):
#     try:
#         msg = f"Запрос на добавление пользователя: \n{request.model_dump()}"
#         await send_email(msg)
#         return JSONResponse(status_code=200, content={'status': True, 'detail': None, 'dev_debug': 'Запрос на регистрацию пользователя отправлен'})
#     except Exception as e:
#         return JSONResponse(status_code=500, content={'status': False, 'detail': 'Ошибка при отправки запроса',
#                                                       'dev_debug': f'Ошибка при отправки запроса на добавление пользователя {request.model_dump()}: {str(e)}'})
#
#
# # ------ Формируем локальный swagger ------------
# def custom_openapi():
#     if app.openapi_schema:
#         return app.openapi_schema
#     openapi_schema = get_openapi(
#         title="Добро пожаловать в Erebus (Filin Portal API)!",
#         version="1.0.0",
#         openapi_version="3.0.0",
#         description="API для публичной и административной частей портала Filin",
#         routes=app.routes,
#     )
#     openapi_schema["info"]["x-logo"] = {
#         "url": "/static/flaticon_cache_icon.png"
#     }
#     app.openapi_schema = openapi_schema
#     return app.openapi_schema
#
# app.openapi = custom_openapi
#
# # Укажем путь до статичных файлов Swagger и подключим их
# PATH_TO_STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'resources', 'static')
# app.mount("/static", StaticFiles(directory=PATH_TO_STATIC), name="static")
#
# @app.get("/redoc", include_in_schema=False)
# async def redoc_html():
#     return get_redoc_html(
#         openapi_url=app.openapi_url,
#         title=app.title + " - ReDoc",
#         redoc_js_url="/static/redoc.standalone.js",
#     )
#
#
# @app.get("/api/docs", include_in_schema=False)
# async def custom_swagger_ui_html() -> HTMLResponse:
#     return get_swagger_ui_html(
#         openapi_url=app.openapi_url,
#         title=app.title + " - Swagger UI",
#         oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
#         swagger_js_url="/static/swagger-ui-bundle.js",
#         swagger_css_url="/static/swagger-ui.css",
#         swagger_favicon_url="/static/favicon-32x32.png",
#     )
#
#
# @app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
# async def swagger_ui_redirect():
#     return get_swagger_ui_oauth2_redirect_html()
# # ------ Завершили формирование локального swagger ------------
#
# # Обработчик глобальных ошибок
# @app.exception_handler(Exception)
# async def global_exception_handler(request: Request, exc: Exception):
#     # Логируем детали запроса и ошибки
#     request_details = {
#         "url": str(request.url),
#         "method": request.method,
#         "client_ip": request.client.host if request.client else None,
#         "headers": {k: v for k, v in request.headers.items() if k.lower() != "authorization"},
#     }
#     logger.error(f"Глобальная ошибка: {exc}", exc_info=True)
#
#     # Возвращаем структурированный ответ
#     return JSONResponse(
#         status_code=500,
#         content={
#             "status": False,
#             "detail": f"Internal Server Error: {exc}",
#             "dev_debug": "Произошла внутренняя ошибка сервера"
#         }
#     )
#
# # Обработчик HTTP ошибок
# @app.exception_handler(HTTPException)
# async def http_exception_handler(request: Request, exc: HTTPException):
#     request_details = {
#         "url": str(request.url),
#         "method": request.method,
#         "client_ip": request.client.host if request.client else None,
#         "headers": {k: v for k, v in request.headers.items() if k.lower() != "authorization"},
#     }
#     logger.error(f"HTTPException: {exc.detail}")
#     # Подготавливаем JSON-ответ
#     response = JSONResponse(
#         status_code=exc.status_code,
#         content={"status": False,
#                  "detail": exc.__class__.__name__,
#                  "dev_debug": exc.detail}
#     )
#     # Если ошибка связана с авторизацией — удаляем токены
#     if exc.status_code in (401, 403):
#         for cookie_name in ["access_token", "refresh_token", "id_token"]:
#             response.delete_cookie(cookie_name, path="/")
#         # Пытаемся завершить сессию в Keycloak через Backchannel Logout
#         refresh_token = request.cookies.get("refresh_token")
#         if refresh_token:
#             await delete_keycloak_session(refresh_token)
#     return response
#
#
# # Добавим кастомный обработчик ошибок и локализацию
# class ErrorTranslator:
#     DEFAULT_ERROR_MESSAGES = {
#         "missing": "Поле обязательно для заполнения",
#         "string_type": "Должно быть строкой",
#         "string_too_short": "Минимум {min_length} символа",
#         "int_parsing": "Должно быть целым числом",
#         "float_parsing": "Должно быть числом",
#         "greater_than": "Должно быть больше {gt}",
#         "less_than_equal": "Должно быть меньше или равно {le}",
#     }
#
#     @classmethod
#     def get_field_title(cls, field) -> str:
#         """Получает title поля модели Pydantic"""
#         if hasattr(field, "title") and field.title:
#             return field.title
#         if hasattr(field, "alias") and field.alias:
#             return field.alias
#         return "Неизвестное поле"
#
#     @classmethod
#     def translate_error(cls, error: dict, model: type[BaseModel] | None = None) -> str:
#         loc = error['loc']
#         error_type = error['type']
#         ctx = error.get('ctx', {})
#
#         # Определяем источник ошибки
#         if loc[0] == "body":
#             # Ошибка в теле запроса (Pydantic модель)
#             if model and len(loc) > 1:
#                 field = model.model_fields.get(loc[1])
#                 field_title = cls.get_field_title(field) if field else loc[1]
#             else:
#                 field_title = "->".join(map(str, loc[1:]))
#         elif loc[0] in ("query", "path", "header", "cookie"):
#             # Ошибка в параметрах запроса
#             field_title = loc[1] if len(loc) > 1 else loc[0]
#         else:
#             field_title = "->".join(map(str, loc))
#
#         # Получаем шаблон сообщения
#         msg_template = cls.DEFAULT_ERROR_MESSAGES.get(error_type, error['msg'])
#
#         # Форматируем сообщение
#         try:
#             message = msg_template.format(**ctx)
#         except KeyError:
#             message = msg_template
#
#         return f"{field_title}: {message}"
#
# @app.exception_handler(RequestValidationError)
# async def validation_handler(request: Request, exc: RequestValidationError):
#     # Преобразуем ошибки в сериализуемый формат
#     errors = []
#     for error in exc.errors():
#         errors.append({
#             "loc": error["loc"],
#             "msg": str(error["msg"]),  # ← Преобразуем в строку!
#             "type": error["type"]
#         })
#     return JSONResponse(status_code=422, content={"detail": errors})
