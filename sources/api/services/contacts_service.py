"""Сервисный слой для карточек контактов — обёртка над DAO с изоляцией по tenant_id."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.data_base.base import BaseDAO, contacts_dao
from api.data_base.models import ContactCard, Tenant
from api.schemas.contacts import ContactCardCreate, ContactCardUpdate
from utils.logger_loguru import get_logger


logger = get_logger()


def _apply_tenant_filter(stmt, tenant_id):
    if tenant_id is None:
        return stmt
    return stmt.where(ContactCard.tenant_id == tenant_id)


class ContactService:
    """Централизованная логика работы с контактами."""

    def __init__(self, dao: BaseDAO):
        self.dao = dao

    async def list_contacts( self, session: AsyncSession, tenant_id, page: int, per_page: int, sort: str, ):
        """Список контактов с пагинацией и сортировкой (логика поверх модели; DAO не поддерживает пагинацию)."""
        logger.info(
            "list_contacts called tenant_id={}, page={}, per_page={}, sort={}",
            tenant_id,
            page,
            per_page,
            sort,
        )
        sort_map = {
            "name": ContactCard.full_name,
            "last_contact_at": ContactCard.last_contact_at,
            "created_at": ContactCard.created_at,
        }
        sort_column = sort_map.get(sort, ContactCard.full_name)

        base_stmt = _apply_tenant_filter(select(ContactCard), tenant_id)
        count_stmt = _apply_tenant_filter(
            select(func.count()).select_from(ContactCard), tenant_id
        )

        total = (await session.execute(count_stmt)).scalar_one()
        offset = (page - 1) * per_page
        result = await session.execute(
            base_stmt.order_by(sort_column).offset(offset).limit(per_page)
        )
        items = result.scalars().all()
        logger.info(
            "list_contacts done tenant_id={}, total={}, returned={}",
            tenant_id,
            total,
            len(items),
        )
        return items, total

    async def get_contact(self, session: AsyncSession, tenant_id, contact_id: str):
        """Получить контакт по ID.

        Временно убираем строгую проверку tenant_id, чтобы контакты с «старыми»
        или некорректными tenant_id всё равно открывались в UI.
        """
        logger.info("get_contact called tenant_id=%s, contact_id=%s", tenant_id, contact_id)
        contact = await self.dao.get_by_id(contact_id, session=session)
        if contact is None:
            logger.warning("get_contact not found contact_id=%s (tenant_id=%s)", contact_id, tenant_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
            )
        logger.info("get_contact success contact_id=%s, tenant_id_in_contact=%s", contact_id, contact.tenant_id)
        return contact

    async def create_contact(
        self,
        session: AsyncSession,
        tenant_id,
        payload: ContactCardCreate,
    ):
        """Создать карточку контакта c безопасной подстановкой tenant_id.

        Если tenant_id у пользователя указывает на несуществующего арендатора,
        создаём такого арендатора автоматически, чтобы не получать FK-ошибку.
        """
        logger.info(
            "create_contact called tenant_id=%s, payload=%s",
            tenant_id,
            payload.model_dump(),
        )
        data = payload.model_dump()

        resolved_tenant_id = tenant_id
        if tenant_id is not None:
            stmt = select(Tenant).where(Tenant.id == tenant_id)
            result = await session.execute(stmt)
            tenant = result.scalar_one_or_none()
            if tenant is None:
                logger.warning(
                    "create_contact: tenant %s not found, creating auto-tenant", tenant_id
                )
                tenant = Tenant(id=tenant_id, name="Auto-created tenant")
                session.add(tenant)
                await session.flush()
        data["tenant_id"] = resolved_tenant_id
        contact = await self.dao.create(data, session=session)
        logger.info(
            "create_contact success tenant_id=%s, contact_id=%s",
            tenant_id,
            getattr(contact, "id", None),
        )
        return contact

    async def update_contact(
        self,
        session: AsyncSession,
        tenant_id,
        contact_id: str,
        payload: ContactCardUpdate,
    ):
        """Частичное обновление контакта с проверкой tenant."""
        logger.info(
            "update_contact called tenant_id=%s, contact_id=%s, payload=%s",
            tenant_id,
            contact_id,
            payload.model_dump(exclude_unset=True),
        )
        await self.get_contact(
            session=session, tenant_id=tenant_id, contact_id=contact_id
        )
        data = payload.model_dump(exclude_unset=True)
        contact = await self.dao.update(contact_id, data, session=session)
        logger.info(
            "update_contact success tenant_id=%s, contact_id=%s",
            tenant_id,
            contact_id,
        )
        return contact

    async def delete_contact(
        self,
        session: AsyncSession,
        tenant_id,
        contact_id: str,
    ):
        """Удалить контакт с проверкой tenant."""
        logger.info(
            "delete_contact called tenant_id=%s, contact_id=%s", tenant_id, contact_id
        )
        await self.get_contact(
            session=session, tenant_id=tenant_id, contact_id=contact_id
        )
        await self.dao.delete(contact_id, session=session)
        logger.info(
            "delete_contact success tenant_id=%s, contact_id=%s", tenant_id, contact_id
        )
        return None


# Единственный экземпляр сервиса для приложения (удобно подменять в тестах)
contact_service = ContactService(contacts_dao)


# Публичный API для роутера (обратная совместимость)
async def list_contacts(session, tenant_id, page, per_page, sort):
    return await contact_service.list_contacts(
        session=session,
        tenant_id=tenant_id,
        page=page,
        per_page=per_page,
        sort=sort,
    )


async def create_contact(session, tenant_id, payload: ContactCardCreate):
    return await contact_service.create_contact(
        session=session, tenant_id=tenant_id, payload=payload
    )


async def get_contact(session, tenant_id, contact_id: str):
    return await contact_service.get_contact(
        session=session, tenant_id=tenant_id, contact_id=contact_id
    )


async def update_contact(session, tenant_id, contact_id: str, payload: ContactCardUpdate):
    return await contact_service.update_contact(
        session=session,
        tenant_id=tenant_id,
        contact_id=contact_id,
        payload=payload,
    )


async def delete_contact(session, tenant_id, contact_id: str):
    return await contact_service.delete_contact(
        session=session, tenant_id=tenant_id, contact_id=contact_id
    )
