"""
Настройка логгера на основе loguru.
"""
import sys
import socket
from pathlib import Path

from loguru import logger

from settings import locate_folder_path, config, LOCAL_DEV

# -------------------- Константы ----------------------

HOSTNAME = socket.gethostname()
_IS_CONFIGURED = False

ROTATION_INTERVAL = config.audit.rotation_interval
RETENTION_PERIOD = config.audit.retention_period

# -------------------- Helpers ----------------------

def format_console_timestamp(record) -> str:
    return record["time"].strftime("%Y-%m-%d %H:%M:%S")

def resolve_log_directory() -> Path:
    """Определяет корректный путь для логов"""
    folder = locate_folder_path()
    if folder is None:
        folder = (Path(__file__).resolve().parents[2] / "logs"
                  if LOCAL_DEV
                  else Path("/code/logs"))
    folder.mkdir(parents=True, exist_ok=True)
    return folder

def build_console_format(json_format: bool) -> str:
    if json_format:
        return "{message}"
    return "<green>{extra[ts]}</green> " + HOSTNAME + " | <level>{level}</level> | {name}:{function}:{line} - <level>{message}</level>"

def build_file_format(json_format: bool) -> str:
    if json_format:
        return "{message}"
    return "{extra[ts]} " + HOSTNAME + " | {level} | {name}:{function}:{line} - {message}"

def configure_level_colors():
    logger.level("INFO", color="<blue>")
    logger.level("WARNING", color="<yellow>")
    logger.level("ERROR", color="<red>")
    logger.level("CRITICAL", color="<red><bold>")


# -------------------- Основная конфигурация ----------------------


def setup_logger_loguru(to_file: bool = True,
                        json_format: bool = False,
                        log_level: str = "INFO",
                        file_name: str = "app.log") -> None:
    global _IS_CONFIGURED
    if _IS_CONFIGURED:
        return

    logger.remove()
    logger.configure(patcher=lambda record: record["extra"].update(ts=format_console_timestamp(record)))

    console_fmt = build_console_format(json_format)
    file_fmt = build_file_format(json_format)

    # STDOUT handler
    logger.add(sys.stdout,
               format=console_fmt,
               level=log_level,
               colorize=not json_format,
               serialize=json_format)
    # FILE handler
    if to_file:
        log_dir = resolve_log_directory()
        log_file = log_dir / file_name
        logger.add(log_file,
                   format=file_fmt,
                   rotation=ROTATION_INTERVAL,
                   retention=RETENTION_PERIOD,
                   compression="zip",
                   level=log_level,
                   serialize=json_format,
                   encoding="utf-8")

    if not json_format:
        configure_level_colors()

    logger.info("Logger configured (stdout{}).".format(" + file" if to_file else ""))
    _IS_CONFIGURED = True


def get_logger():
    return logger


# Backward compatibility for old audit API
def setup_audit_logger_loguru(to_file: bool = True,
                              json_format: bool = False,
                              log_level: str = "INFO") -> None:
    setup_logger_loguru(to_file=to_file, json_format=json_format, log_level=log_level)


def get_audit_logger():
    return get_logger()
