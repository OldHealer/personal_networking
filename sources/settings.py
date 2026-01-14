import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource
from pydantic import SecretStr, BaseModel, Field

logger = logging.getLogger(__name__)

LOCAL_DEV: bool = False # Флаг для локального запуска с IDE и миграций

class ApiSettings(BaseModel):
    """Настройки API сервера"""
    host: str = Field(default="0.0.0.0", description="Хост для запуска API сервера")
    port: int = Field(default=8000, gt=0, le=65535, description="Порт для API сервера")
    workers: int = Field(default=1, ge=1, description="Количество рабочих процессов")
    base_url: str = Field(default="http://localhost:3000", description="URL frontend")
    verify_ssl: bool = Field(default=True, description="Флаг проверки сертификата")
    ssl_keyfile: str | None = Field(default=None, description="Путь до ключа сертификата")
    ssl_certfile: str | None = Field(default=None, description="Путь до файла сертификата")
    environment: Literal["DEV", "TEST", "STAGE", "PROD"] = Field(default='DEV', description="Среда запуска сервиса")
    cache_size: int = Field(default=2048, description="Максимальное количество объектов для кэширования")
    cache_ttl: int = Field(default=3600, description="Максимальное время кэширования объектов в секундах")

class DataBaseSettings(BaseModel):
    """Настройки Базы данных"""
    db_driver: str = Field(default="postgresql+asyncpg", description="Драйвер подключения к БД")
    db_user: str = Field(..., description="Пользователь БД")
    db_password: SecretStr = Field(..., description="Пароль пользователя БД")
    db_host: str = Field(..., description="Хост БД")
    db_port: int = Field(..., description="Порт БД")
    db_name: str = Field(..., description="Имя БД")
    db_pool_size: int = Field(default=20, description="Основное количество постоянных соединений в пуле")
    db_pool_timeout: float = Field(default=30.0, description="Таймаут получения соединения из пула (в секундах)")
    db_max_overflow: int = Field(default=30.0, description="Количество дополнительных соединений, которые могут быть созданы поверх основного пула при его исчерпании")

    @property
    def database_url(self) -> str:
        return f"{self.db_driver}://{self.db_user}:{self.db_password.get_secret_value()}@{self.db_host}:{self.db_port}/{self.db_name}"

class SMTPSettings(BaseModel):
    """Настройки для отправки email"""
    login: str | None = Field(None, description="Логин для подключения к SMTP-серверу")
    password: SecretStr | None = Field(None, description="Пароль для подключения к SMTP-серверу")
    host: str | None = Field(None, description="Хост SMTP-сервера")
    port: int | None = Field(None, description="Порт SMTP-сервера")
    send_to: list[str] = Field(default_factory=list, description="Список адресов электронной почты, на которые будут отправляться письма")

class TokensSettings(BaseModel):
    """Настройки шифрования"""
    secret_key: SecretStr = Field(..., description="Секретная строка шифрования токена")

class Audit(BaseModel):
    """Настройки аудит-логирования"""
    enabled: bool = Field(default=True, description="Флаг включения/отключения аудит-логирования")
    min_severity: int = Field(default=3, ge=0, le=10, description="Минимальный уровень серьезности для логирования (0-10). События с severity меньше этого значения не будут логироваться")
    rotation_interval: str = Field(default="7 days", description="Период ротации логов")
    retention_period: str = Field(default="30 days", description="Период хранения логов")

class Settings(BaseSettings):
    """
    Класс настроек приложения

    Attributes:
        api: Настройки API сервера
        database: Настройки базы данных
        smpt: Настройки SMTP для отправки email
        token: Настройки для токенов и шифрования
        alembic_ini_path: Путь до конфигурации Alembic для миграций
        audit: Настройки аудит логгера
    """

    @staticmethod
    def _get_env_file_path() -> str:
        """Определяет путь к .env файлу на основе флага LOCAL_DEV"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.join(base_dir, '..')
        # Если установлен флаг локальной разработки
        if LOCAL_DEV:
            return os.path.join(project_root, '.env.local')
        # Иначе используем стандартный .env
        return os.path.join(project_root, '.env')

    model_config = SettingsConfigDict(env_file=_get_env_file_path(),
                                      env_file_encoding="utf-8",
                                      case_sensitive=False,
                                      extra="ignore",
                                      env_nested_delimiter="__")

    api: ApiSettings = Field(default_factory=ApiSettings, description="Настройки API сервера")
    database: DataBaseSettings = Field(default_factory=DataBaseSettings, description="Настройки Базы Данных")
    smpt: SMTPSettings = Field(default_factory=SMTPSettings, description="Настройки email почты")
    token: TokensSettings = Field(default_factory=TokensSettings, description="Настройки для токенов и шифрования")
    alembic_ini_path: str | None = Field(None, description="Путь до alembic.ini")
    audit: Audit = Field(default_factory=Audit, description="Настройки аудит логгера")


    @property
    def alembic_path(self) -> str:
        """
        Возвращает путь к конфигурационному файлу Alembic
        Если alembic_ini_path не задан, автоматически ищет alembic.ini в корне проекта (на уровень выше директории sources)

        :return: Путь к alembic.ini файлу
        """
        if self.alembic_ini_path:  # если явно задано
            return self.alembic_ini_path
        # автоопределение: ищем alembic.ini в корне проекта
        project_root = Path(__file__).resolve().parent.parent  # /code/sources → /code
        return str(project_root / "alembic.ini")


def locate_folder_path(folder_name: str = 'logs') -> Path | None:
    """Метод поиска папки относительно пути нахождения"""
    abspath = Path(__file__).absolute()
    for parent in abspath.parents:
        target_path = parent.joinpath(folder_name)
        if target_path.exists() and target_path.is_dir():
            return target_path
    return None


config = Settings()
