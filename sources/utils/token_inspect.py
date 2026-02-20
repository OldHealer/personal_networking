"""
Скрипт для проверки и детального просмотра JWT токена.

Пример использования:
1) Через аргумент:
   python sources/utils/token_inspect.py <ACCESS_TOKEN>
2) Через переменную окружения:
   set TOKEN=eyJ... (Windows)
   TOKEN=eyJ... python sources/utils/token_inspect.py (Linux/Mac)
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path, чтобы работали импорты из sources/*
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from sources.api.auth.keycloak_module import verify_jwt_token  


async def main() -> None:
    # Берём токен либо из аргумента, либо из переменной окружения TOKEN
    token = None
    if len(sys.argv) > 1:
        token = sys.argv[1]
    if not token:
        token = os.getenv("TOKEN")

    if not token:
        print("Передайте токен аргументом или через переменную окружения TOKEN.")
        sys.exit(1)

    payload = await verify_jwt_token(token)
    print(json.dumps(payload.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())