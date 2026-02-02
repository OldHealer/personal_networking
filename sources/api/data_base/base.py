# import re
# from datetime import datetime, UTC, timedelta
#
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from sqlalchemy import asc, desc, func, and_, or_
# from sqlalchemy.orm import selectinload
#
# from settings import config
# from utils.sqlalchemy_base_crud import Database, BaseDAO
# from erebus_db.models import (LLMModelRegistry, WorkerModelRegistry, LLMModelInstanceRegistry, PluginModelRegistry,
#                               UserModelRegistry, UserGroup, UserGroupMembership, Source, AccessPolicy, PolicySource,
#                               PolicyGroup, SourceGit, SourceDoc, Cluster, TokenStatus)
# from utils.sqlalchemy_base_crud.data_access_object import with_session
# from api.schemas.user_groups import UserGroupInfo, GroupMember
#
# db = Database(config.database.database_url, pool_size=config.database.db_pool_size, max_overflow=config.database.db_max_overflow, pool_timeout=config.database.db_pool_timeout)
#
#
# class LLMModelDAO(BaseDAO):
#     def __init__(self, model, database=None):
#         super().__init__(model, database)
#
#     @with_session
#     async def find_models_by_mode_with_pagination(
#             self,
#             session: AsyncSession = None,
#             mode: str = None,
#             page: int = 1,
#             per_page: int = 100,
#             order_by: str = None,
#             order_direction: str = "asc"
#     ):
#         data_query = select(self.model).where(self.model.modes.any(mode))
#
#         # Сортировка
#         if order_by:
#             column = getattr(self.model, order_by, None)
#             if column:
#                 if order_direction.lower() == "desc":
#                     data_query = data_query.order_by(desc(column))
#                 else:
#                     data_query = data_query.order_by(asc(column))
#
#         # Пагинация
#         offset = (page - 1) * per_page
#         data_query = data_query.offset(offset).limit(per_page)
#
#         result = (await session.execute(data_query)).scalars().all()
#         return result
#
# class SourceGroupsDAO(BaseDAO):
#     """Специальный DAO для работы с источниками и их группами доступа"""
#
#     def __init__(self, model, database=None):
#         super().__init__(model, database)
#
#     @with_session
#     async def get_source_groups_info(self, session: AsyncSession = None, source_id: str = None):
#         """Получает список групп с доступом к источнику в формате UserGroupInfo"""
#
#
#         try:
#             # SQL-запрос для получения групп с доступом к источнику
#             groups_query = select(
#                 UserGroup.id.label('group_id'),
#                 UserGroup.name.label('group_name'),
#                 UserGroup.created_at,
#                 UserGroup.updated_at,
#                 UserGroup.tabby_group_id,
#                 func.count(UserGroupMembership.id).label('members_count')
#             ).select_from(
#                 Source
#             ).join(
#                 PolicySource, Source.id == PolicySource.source_id
#             ).join(
#                 AccessPolicy, PolicySource.policy_id == AccessPolicy.id
#             ).join(
#                 UserGroup, AccessPolicy.name == UserGroup.name
#             ).outerjoin(
#                 UserGroupMembership, UserGroup.id == UserGroupMembership.group_id
#             ).where(
#                 Source.id == source_id
#             ).group_by(
#                 UserGroup.id, UserGroup.name, UserGroup.created_at, UserGroup.updated_at, UserGroup.tabby_group_id
#             ).order_by(
#                 UserGroup.name
#             )
#
#             groups_result = await session.execute(groups_query)
#             groups_records = groups_result.fetchall()
#
#             # Преобразуем записи в UserGroupInfo
#             groups_info = []
#             for record in groups_records:
#                 # Получаем участников группы с email через связь с пользователем
#                 members_query = select(
#                     UserGroupMembership.id,
#                     UserGroupMembership.role_in_group,
#                     UserModelRegistry.email.label('user_email')
#                 ).join(
#                     UserModelRegistry, UserGroupMembership.user_id == UserModelRegistry.id
#                 ).where(
#                     UserGroupMembership.group_id == record.group_id
#                 )
#
#                 members_result = await session.execute(members_query)
#                 members_records = members_result.fetchall()
#
#                 # Преобразуем участников в GroupMember
#                 members = []
#                 for member_record in members_records:
#                     member = GroupMember(
#                         id=member_record.id,
#                         role_in_group=member_record.role_in_group,
#                         user_email=member_record.user_email
#                     )
#                     members.append(member)
#
#                 # Создаем UserGroupInfo
#                 group_info = UserGroupInfo(
#                     id=record.group_id,
#                     name=record.group_name,
#                     createdAt=record.created_at,
#                     updatedAt=record.updated_at,
#                     membersCount=record.members_count,
#                     members=members,
#                     tabby_group_id=record.tabby_group_id
#                 )
#                 groups_info.append(group_info)
#             return groups_info
#
#         except Exception as e:
#             import logging
#             logger = logging.getLogger(__name__)
#             logger.error(f"Ошибка при получении групп для источника {source_id}: {e}")
#             return []
#
#     @with_session
#     async def get_tabby_source_id(
#             self,
#             session: AsyncSession = None,
#             source: Source = None
#     ):
#         """Получает tabby_source_id из детальной таблицы источника"""
#         import logging
#         logger = logging.getLogger(__name__)
#
#         try:
#             tabby_source_id = None
#
#             if source.type == "git":
#                 git_query = select(SourceGit).where(SourceGit.id == source.id)
#                 git_result = await session.execute(git_query)
#                 git_source = git_result.scalar_one_or_none()
#                 if git_source and git_source.options and git_source.options.get("tabby_source_id"):
#                     tabby_source_id = git_source.options["tabby_source_id"]
#
#             elif source.type == "doc":
#                 doc_query = select(SourceDoc).where(SourceDoc.id == source.id)
#                 doc_result = await session.execute(doc_query)
#                 doc_source = doc_result.scalar_one_or_none()
#                 if doc_source and doc_source.options and doc_source.options.get("tabby_source_id"):
#                     tabby_source_id = doc_source.options["tabby_source_id"]
#
#             return tabby_source_id
#
#         except Exception as err:
#             logger.exception(err)
#             return None
#
#     @with_session
#     async def get_source_detailed_data(
#             self,
#             session: AsyncSession = None,
#             source: Source = None
#     ):
#         """Получает детальные данные источника в зависимости от его типа"""
#         import logging
#         logger = logging.getLogger(__name__)
#
#         try:
#             detailed_data = {}
#
#             if source.type == "git":
#                 git_query = select(SourceGit).where(SourceGit.id == source.id)
#                 git_result = await session.execute(git_query)
#                 git_source = git_result.scalar_one_or_none()
#                 if git_source:
#                     detailed_data = {
#                         "git_url": git_source.git_url,
#                         "branch": git_source.branch,
#                         "access_token": git_source.access_token,
#                         "ssh_key": git_source.ssh_key,
#                         "options": git_source.options,
#                         "http_headers": git_source.http_headers,
#                         "proxy_url": git_source.proxy_url
#                     }
#             elif source.type == "doc":
#                 doc_query = select(SourceDoc).where(SourceDoc.id == source.id)
#                 doc_result = await session.execute(doc_query)
#                 doc_source = doc_result.scalar_one_or_none()
#                 if doc_source:
#                     detailed_data = {
#                         "url": doc_source.url,
#                         "doc_metadata": doc_source.doc_metadata,
#                         "options": doc_source.options,
#                         "http_headers": doc_source.http_headers,
#                         "proxy_url": doc_source.proxy_url
#                     }
#             return detailed_data
#
#         except Exception as err:
#             logger.exception(f"Ошибка при получении детальных данных для источника {source.id}: {err}")
#             return {}
#
#     @with_session
#     async def check_user_source_access(
#             self,
#             session: AsyncSession = None,
#             user_id: str = None,
#             source_id: str = None
#     ):
#         """Проверяет доступ пользователя к источнику через группы"""
#         try:
#             # Выполняем SQL-запрос для проверки доступа через группы пользователя
#             access_query = select(
#                 PolicySource.can_read,
#                 PolicySource.can_write,
#                 PolicySource.can_manage,
#                 PolicySource.row_filter,
#                 PolicySource.column_mask,
#                 AccessPolicy.name.label('policy_name'),
#                 UserGroup.name.label('group_name')
#             ).select_from(
#                 UserModelRegistry
#             ).join(
#                 UserGroupMembership, UserModelRegistry.id == UserGroupMembership.user_id
#             ).join(
#                 UserGroup, UserGroupMembership.group_id == UserGroup.id
#             ).join(
#                 AccessPolicy, AccessPolicy.name == UserGroup.name
#             ).join(
#                 PolicySource, AccessPolicy.id == PolicySource.policy_id
#             ).where(
#                 UserModelRegistry.id == user_id,
#                 PolicySource.source_id == source_id
#             )
#
#             access_result = await session.execute(access_query)
#             access_records = access_result.fetchall()
#             return access_records
#
#         except Exception as e:
#             import logging
#             logger = logging.getLogger(__name__)
#             logger.error(f"Ошибка при проверке доступа пользователя {user_id} к источнику {source_id}: {e}")
#             return []
#
#     @with_session
#     async def get_source_groups_access(
#         self,
#         session: AsyncSession = None,
#         source_id: str = None
#     ):
#         """Получает список групп с доступом к источнику данных"""
#         try:
#             # Выполняем SQL-запрос для получения групп с доступом к источнику
#             groups_query = select(
#                 UserGroup.id.label('group_id'),
#                 UserGroup.name.label('group_name'),
#                 AccessPolicy.id.label('policy_id'),
#                 AccessPolicy.name.label('policy_name'),
#                 PolicySource.can_read,
#                 PolicySource.can_write,
#                 PolicySource.can_manage,
#                 PolicySource.row_filter,
#                 PolicySource.column_mask,
#                 PolicySource.created_at.label('assigned_at')
#             ).select_from(
#                 Source
#             ).join(
#                 PolicySource, Source.id == PolicySource.source_id
#             ).join(
#                 AccessPolicy, PolicySource.policy_id == AccessPolicy.id
#             ).join(
#                 UserGroup, AccessPolicy.name == UserGroup.name
#             ).where(
#                 Source.id == source_id
#             ).order_by(
#                 UserGroup.name, AccessPolicy.name
#             )
#
#             groups_result = await session.execute(groups_query)
#             groups_records = groups_result.fetchall()
#             return groups_records
#
#         except Exception as e:
#             import logging
#             logger = logging.getLogger(__name__)
#             logger.error(f"Ошибка при получении групп с доступом к источнику {source_id}: {e}")
#             return []
#
#     @with_session
#     async def get_group_sources_access(
#             self,
#             session: AsyncSession = None,
#             group_name: str = None
#     ):
#         """Получает список источников, доступных группе"""
#         try:
#             # Выполняем SQL-запрос для получения источников с доступом к группе
#             sources_query = select(
#                 Source.id.label('source_id'),
#                 Source.name.label('source_name'),
#                 Source.type.label('source_type'),
#                 Source.description.label('source_description'),
#                 AccessPolicy.id.label('policy_id'),
#                 AccessPolicy.name.label('policy_name'),
#                 PolicySource.can_read,
#                 PolicySource.can_write,
#                 PolicySource.can_manage,
#                 PolicySource.row_filter,
#                 PolicySource.column_mask,
#                 PolicySource.created_at.label('assigned_at')
#             ).select_from(
#                 Source
#             ).join(
#                 PolicySource, Source.id == PolicySource.source_id
#             ).join(
#                 AccessPolicy, PolicySource.policy_id == AccessPolicy.id
#             ).where(
#                 AccessPolicy.name == group_name
#             ).order_by(
#                 Source.name, AccessPolicy.name
#             )
#
#             sources_result = await session.execute(sources_query)
#             sources_records = sources_result.fetchall()
#             return sources_records
#
#         except Exception as e:
#             import logging
#             logger = logging.getLogger(__name__)
#             logger.error(f"Ошибка при получении источников с доступом к группе {group_name}: {e}")
#             return []
#
# class WorkerDAO(BaseDAO):
#     def __init__(self, model, database=None):
#         super().__init__(model, database)
#
#     @with_session
#     async def get_workers_with_llm_instances(self, session: AsyncSession = None, cluster_gpustack_id: int | None = None):
#         """
#         Возвращает воркеры кластера с llm-инстансами и моделями. Кластер идентифицируется по его реальному ID из GPUStack.
#         """
#         workers_stmt = (
#             select(WorkerModelRegistry)
#             .where(WorkerModelRegistry.cluster_id == cluster_gpustack_id)
#             .options(selectinload(WorkerModelRegistry.cluster))
#         )
#         workers = (await session.execute(workers_stmt)).scalars().all()
#
#         instances_stmt = select(LLMModelInstanceRegistry).where(LLMModelInstanceRegistry.cluster_id == cluster_gpustack_id)
#         instances = (await session.execute(instances_stmt)).scalars().all()
#
#         instances_by_worker: dict[str, list[LLMModelInstanceRegistry]] = {}
#         for instance in instances:
#             for worker_id in getattr(instance, "worker_node_ids", None) or []:
#                 instances_by_worker.setdefault(worker_id, []).append(instance)
#
#         for worker in workers:
#             setattr(worker, 'llm_instances', instances_by_worker.get(worker.id, []))
#
#         return workers
#
#     @with_session
#     async def get_workers_with_gpu_devices(self, session: AsyncSession = None, cluster_gpustack_id: int | None = None):
#         """
#         Возвращает воркеры кластера с GPU данными. Кластер идентифицируется по его реальному ID из GPUStack.
#         """
#         stmt = (
#             select(WorkerModelRegistry)
#             .where(WorkerModelRegistry.cluster_id == cluster_gpustack_id)
#             .options(
#                 selectinload(WorkerModelRegistry.cluster)
#             )
#         )
#         result = await session.execute(stmt)
#         return result.scalars().all()
#
# class UserModelDAO(BaseDAO):
#     def __init__(self, model, database=None):
#         super().__init__(model, database)
#
#     @with_session
#     async def find_expired_tokens(self, ttl_days: int, session: AsyncSession = None):
#         """
#         Возвращает список пользователей, у которых срок действия Litellm-токена истёк.
#
#         Метод вычисляет момент "истечения" токена как:
#         datetime.now(UTC) - timedelta(days=ttl)
#
#         После этого выбираются все записи, у которых:
#             - поле litellm_token_created_at задано (не NULL),
#             - дата создания токена меньше рассчитанного expire_before,
#             - токен еще не заблокирован (key_blocked = False).
#
#         :param ttl: Период жизни токена в днях. Если токен старше этого периода, он считается просроченным.
#         :param session: Асинхронная сессия SQLAlchemy
#         :return: list[UserModel] Список ORM-объектов пользователей, чьи токены истекли, но еще не заблокированы.
#         """
#         expire_before = datetime.now(UTC) - timedelta(days=ttl_days)
#         stmt = (
#             select(self.model)
#             .where(
#                 and_(
#                     self.model.litellm_token_created_at.is_not(None),
#                     self.model.litellm_token_created_at < expire_before,
#                     self.model.token_status == TokenStatus.ACTIVE.value,
#                 )
#             )
#         )
#         result = await session.execute(stmt)
#         return result.scalars().all()
#
#     @with_session
#     async def find_unexpired_but_marked_expired(self, ttl_days: int, session: AsyncSession = None):
#         """
#         Найти пользователей, у которых статус токена отмечен как EXPIRED,
#         но по-текущему TTL токен уже не считается просроченным.
#
#         Эта функция используется для восстановления токенов, когда TTL был
#         увеличен в настройках сервиса. Например, токен был создан 10 дней назад,
#         TTL раньше был 7 дней, но после изменения TTL на 30 дней токен снова
#         попадает в диапазон допустимых.
#
#         Критерии выбора пользователя:
#           - статус токена равен ``TokenStatus.EXPIRED``;
#           - значение ``litellm_token_created_at`` больше или равно
#             вычисленной границе ``now - ttl_days``.
#
#         :param ttl_days: Период жизни токена в днях
#         :param session: Асинхронная сессия SQLAlchemy
#         :return: list[UserModel] Список пользователей, статус которых необходимо откатить обратно на ACTIVE.
#         """
#         expire_before = datetime.now(UTC) - timedelta(days=ttl_days)
#         stmt = (
#             select(self.model)
#             .where(
#                 and_(
#                     self.model.token_status == TokenStatus.EXPIRED.value,
#                     self.model.litellm_token_created_at >= expire_before,  # по новым правилам не истёк
#                 )
#             )
#         )
#
#         result = await session.execute(stmt)
#         return result.scalars().all()
#
#     @with_session
#     async def find_all_with_pagination_and_search(self, session: AsyncSession = None, page: int = 1,
#                                                   per_page: int = 100,
#                                                   order_direction: str = "asc",
#                                                   search: str = None,
#                                                   return_total: bool = False,
#                                                   sort_in_memory: bool = True):
#         """
#         Асинхронно находит и возвращает экземпляры модели с поддержкой сортировки, пагинации, лимитов и поиска.
#
#         :param session: сессия
#         :param page: номер страницы (начиная с 1)
#         :param per_page: количество элементов на странице
#         :param order_direction: направление сортировки ('asc' или 'desc')
#         :param search: строка для поиска по имени и email (игнорирует регистр)
#         :param return_total: флаг, возврата количества
#         :param sort_in_memory: если True, сортировка выполняется в памяти после получения всех данных
#         :return: список экземпляров модели, удовлетворяющих критериям
#         """
#         # Базовый запрос для данных (ВСЕХ данных без пагинации)
#         data_query = select(self.model)
#
#         # Запрос для подсчета общего количества
#         count_query = select(func.count()).select_from(self.model)
#
#         if search:
#             search_clean = search.strip().lower()
#             search_pattern = f"%{search_clean}%"
#
#             # ВАЖНО: Используем func.lower() для регистронезависимого поиска
#             condition = or_(
#                 func.lower(self.model.full_name).ilike(search_pattern),
#                 func.lower(self.model.email).ilike(search_pattern)
#             )
#             data_query = data_query.where(condition)
#             count_query = count_query.where(condition)
#
#         # ВАЖНО: сначала получаем ВСЕ данные, без пагинации
#         result = await session.execute(data_query)
#         all_items = result.scalars().all()
#
#         # Сортируем в памяти
#         latin_re = re.compile(r'^[A-Za-z]')
#         cyrillic_re = re.compile(r'^[А-Яа-яЁё]')
#         if sort_in_memory and all_items:
#             def sort_key(item):
#                 name = item.full_name or ""
#
#                 if latin_re.match(name):
#                     priority = 0  # латиница
#                 elif cyrillic_re.match(name):
#                     priority = 1  # кириллица
#                 else:
#                     priority = 2
#                 return priority, name.casefold()
#
#             # Сортируем все элементы
#             all_items.sort(key=sort_key)
#
#             # Если нужна обратная сортировка
#             if order_direction.lower() == "desc":
#                 all_items.reverse()
#
#         # Применяем пагинацию ПОСЛЕ сортировки
#         offset = (page - 1) * per_page
#         items = all_items[offset:offset + per_page]
#
#         if return_total:
#             # Выполняем запрос подсчета
#             count_result = await session.execute(count_query)
#             total = count_result.scalar()
#             return items, total
#         else:
#             return items
#
# llm_model_dao = LLMModelDAO(LLMModelRegistry)
# worker_dao = WorkerDAO(WorkerModelRegistry)
# llm_instance_dao = BaseDAO(LLMModelInstanceRegistry)
# plugin_dao = BaseDAO(PluginModelRegistry)
# user_dao = UserModelDAO(UserModelRegistry)
# groups_dao = BaseDAO(UserGroup)
# memberships_dao = BaseDAO(UserGroupMembership)
# sources_dao = BaseDAO(Source)
# source_groups_dao = SourceGroupsDAO(Source)
# source_git_dao = BaseDAO(SourceGit)
# source_doc_dao = BaseDAO(SourceDoc)
# access_policies_dao = BaseDAO(AccessPolicy)
# policy_sources_dao = BaseDAO(PolicySource)
# policy_groups_dao = BaseDAO(PolicyGroup)
# git_dao = BaseDAO(SourceGit, db)
# doc_dao = BaseDAO(SourceDoc, db)
# cluster_dao = BaseDAO(Cluster)


from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Awaitable

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from settings import config
from api.data_base.models import (
    Base,
    ContactCard,
    ContactFamilyMember,
    ContactInteraction,
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


db = Database(config.database.database_url,
              pool_size=config.database.db_pool_size,
              max_overflow=config.database.db_max_overflow,
              pool_timeout=config.database.db_pool_timeout,)


contacts_dao = BaseDAO(ContactCard, db)
family_members_dao = BaseDAO(ContactFamilyMember, db)
interactions_dao = BaseDAO(ContactInteraction, db)
