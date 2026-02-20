import asyncio
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from settings import config


async def ensure_database_exists() -> bool:
    """Создаёт БД, если её нет. Возвращает True, если БД уже существовала."""
    db_name = config.database.db_name
    admin_url = URL.create(
        drivername=config.database.db_driver,
        username=config.database.db_user,
        password=config.database.db_password.get_secret_value(),
        host=config.database.db_host,
        port=config.database.db_port,
        database="postgres",
    )

    engine = create_async_engine(admin_url)
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
            {"db_name": db_name},
        )
        exists = result.scalar() is not None
        if not exists:
            await conn.execution_options(isolation_level="AUTOCOMMIT").execute(
                text(f'CREATE DATABASE "{db_name}"')
            )
    await engine.dispose()
    return exists


def run_migrations() -> None:
    """Запускает alembic upgrade head."""
    alembic_ini = config.alembic_path
    cmd = [sys.executable, "-m", "alembic", "-c", alembic_ini, "upgrade", "head"]
    subprocess.run(cmd, check=True)


async def main() -> None:
    existed = await ensure_database_exists()
    if existed:
        print("БД существует. Применяю миграции...")
    else:
        print("БД отсутствовала. Создал БД и применяю миграции...")
    run_migrations()
    print("Готово.")


if __name__ == "__main__":
    asyncio.run(main())
