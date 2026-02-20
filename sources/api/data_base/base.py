from collections.abc import AsyncIterator, Callable, Awaitable

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from settings import config
from api.data_base.models import (
    Base,
    ContactCard,
    ContactFamilyMember,
    ContactInteraction,
    AppUser,
    ContactLink,
    Tenant,
)


class Database:
    """Минимальная обёртка над Async SQLAlchemy."""

    def __init__(self, database_url: str, pool_size: int, max_overflow: int, pool_timeout: float):
        self.engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            future=True,
        )
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def get_session(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as session:
            yield session

    async def check_connection(self) -> bool:
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def init_models(self, base: type[Base]) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(base.metadata.create_all)


def with_session(func: Callable[..., Awaitable]):
    """Декоратор: если сессия не передана, создаём её автоматически."""

    async def wrapper(self, *args, **kwargs):
        session = kwargs.get("session")
        if session is not None:
            return await func(self, *args, **kwargs)
        async for session in self.database.get_session():
            kwargs["session"] = session
            return await func(self, *args, **kwargs)

    return wrapper


class BaseDAO:
    """Простейший DAO для CRUD-операций."""

    def __init__(self, model, database: Database):
        self.model = model
        self.database = database

    @with_session
    async def create(self, data: dict, session: AsyncSession):
        obj = self.model(**data)
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

    @with_session
    async def get_by_id(self, item_id, session: AsyncSession):
        result = await session.execute(select(self.model).where(self.model.id == item_id))
        return result.scalar_one_or_none()

    @with_session
    async def list_all(self, session: AsyncSession):
        result = await session.execute(select(self.model))
        return result.scalars().all()

    @with_session
    async def update(self, item_id, data: dict, session: AsyncSession):
        obj = await self.get_by_id(item_id=item_id, session=session)
        if obj is None:
            return None
        for key, value in data.items():
            setattr(obj, key, value)
        await session.commit()
        await session.refresh(obj)
        return obj

    @with_session
    async def delete(self, item_id, session: AsyncSession):
        obj = await self.get_by_id(item_id=item_id, session=session)
        if obj is None:
            return False
        await session.delete(obj)
        await session.commit()
        return True

async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Dependency для FastAPI: получить сессию БД."""
    async for session in db.get_session():
        yield session


db = Database(config.database.database_url,
              pool_size=config.database.db_pool_size,
              max_overflow=config.database.db_max_overflow,
              pool_timeout=config.database.db_pool_timeout,)

users_dao = BaseDAO(AppUser, db)
contacts_dao = BaseDAO(ContactCard, db)
family_members_dao = BaseDAO(ContactFamilyMember, db)
interactions_dao = BaseDAO(ContactInteraction, db)
tenants_dao = BaseDAO(Tenant, db)
contact_links_dao = BaseDAO(ContactLink, db)


