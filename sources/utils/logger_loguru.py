"""
Настройка аудит-логгера на основе loguru.
"""
# import sys
# import socket
# from pathlib import Path
# from loguru import logger
#
# from settings import locate_folder_path, config, LOCAL_DEV
#
# # -------------------- Константы ----------------------
#
# AUDIT_TAGS = ["audit", "cef"]
# HOSTNAME = socket.gethostname()
# _IS_CONFIGURED = False
#
# ROTATION_INTERVAL = config.audit.rotation_interval
# RETENTION_PERIOD = config.audit.retention_period
#
# # -------------------- Helpers ----------------------
#
# def format_cef_timestamp(record) -> str:
#     """Формат для CEF: Dec 11 2025 17:04:58"""
#     return record["time"].strftime("%b %d %Y %H:%M:%S")
#
# def patch_record(record):
#     record["extra"]["cef_timestamp"] = format_cef_timestamp(record)
#
# def resolve_log_directory() -> Path:
#     """Определяет корректный путь для логов"""
#     folder = locate_folder_path()
#     if folder is None:
#         folder = (Path(__file__).resolve().parents[2] / "logs"
#                   if LOCAL_DEV
#                   else Path("/code/logs"))
#     folder.mkdir(parents=True, exist_ok=True)
#     return folder
#
# def audit_filter(record) -> bool:
#     """Пропускаем только audit=True"""
#     return record["extra"].get("audit", False)
#
# def build_console_format(json_format: bool) -> str:
#     if json_format:
#         return "{message}"
#     return "<green>{extra[cef_timestamp]}</green> " + HOSTNAME + " <level>{message}</level>"
#
# def build_file_format(json_format: bool) -> str:
#     if json_format:
#         return "{message}"
#     return "{extra[cef_timestamp]} " + HOSTNAME + " {message}"
#
# def configure_level_colors():
#     logger.level("INFO", color="<blue>")
#     logger.level("WARNING", color="<yellow>")
#     logger.level("ERROR", color="<red>")
#     logger.level("CRITICAL", color="<red><bold>")
#
# # -------------------- Основная конфигурация ----------------------
#
# def setup_audit_logger_loguru(to_file: bool = True,
#                               json_format: bool = False,
#                               log_level: str = "INFO") -> None:
#     global _IS_CONFIGURED
#     if _IS_CONFIGURED:
#         return
#
#     logger.remove()
#     logger.configure(patcher=patch_record)
#
#     console_fmt = build_console_format(json_format)
#     file_fmt = build_file_format(json_format)
#
#     # STDOUT handler
#     logger.add(sys.stdout,
#                format=console_fmt,
#                level=log_level,
#                colorize=not json_format,
#                serialize=json_format,
#                filter=audit_filter, )
#     # FILE handler
#     if to_file:
#         log_dir = resolve_log_directory()
#         log_file = log_dir / "audit.log"
#         logger.add(log_file,
#                    format=file_fmt,
#                    rotation=ROTATION_INTERVAL,
#                    retention=RETENTION_PERIOD,
#                    compression="zip",
#                    level=log_level,
#                    serialize=json_format,
#                    encoding="utf-8",
#                    filter=audit_filter, )
#
#     if not json_format:
#         configure_level_colors()
#
#     audit_logger = logger.bind(audit=True)
#     audit_logger.info("Audit logger configured (stdout{}).".format(" + file" if to_file else ""))
#     _IS_CONFIGURED = True
#
# def get_audit_logger():
#     return logger.bind(audit=True)
