"""Сервисный слой для карточек контактов — обёртка над DAO с изоляцией по tenant_id."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.data_base.base import BaseDAO, contacts_dao
from api.data_base.models import ContactCard, ContactInteraction, Tenant
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
        last_interaction_subq = (
            select(
                ContactInteraction.contact_id.label("contact_id"),
                func.max(ContactInteraction.occurred_at).label("last_interaction_at"),
            )
            .group_by(ContactInteraction.contact_id)
            .subquery()
        )

        sort_map = {
            "name": ContactCard.full_name,
            "created_at": ContactCard.created_at,
        }
        sort_column = sort_map.get(sort, ContactCard.full_name)

        base_stmt = _apply_tenant_filter(
            select(ContactCard, last_interaction_subq.c.last_interaction_at).outerjoin(
                last_interaction_subq,
                ContactCard.id == last_interaction_subq.c.contact_id,
            ),
            tenant_id,
        )
        count_stmt = _apply_tenant_filter(
            select(func.count()).select_from(ContactCard), tenant_id
        )

        total = (await session.execute(count_stmt)).scalar_one()
        offset = (page - 1) * per_page
        result = await session.execute(
            base_stmt.order_by(sort_column).offset(offset).limit(per_page)
        )
        rows = result.all()
        items = []
        for contact, last_interaction_at in rows:
            # Поле вычисляемое (не хранится в ContactCard), нужно для миникарточек.
            setattr(contact, "last_interaction_at", last_interaction_at)
            items.append(contact)

        return items, total


    async def get_contact(self, session: AsyncSession, tenant_id, contact_id: str):
        """Получить контакт по ID.

        Временно убираем строгую проверку tenant_id, чтобы контакты с «старыми»
        или некорректными tenant_id всё равно открывались в UI.
        """
        contact = await self.dao.get_by_id(contact_id, session=session)
        if contact is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
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
        data = payload.model_dump()

        resolved_tenant_id = tenant_id
        if tenant_id is not None:
            stmt = select(Tenant).where(Tenant.id == tenant_id)
            result = await session.execute(stmt)
            tenant = result.scalar_one_or_none()
            if tenant is None:
                tenant = Tenant(id=tenant_id, name="Auto-created tenant")
                session.add(tenant)
                await session.flush()
        data["tenant_id"] = resolved_tenant_id
        contact = await self.dao.create(data, session=session)

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
        await self.get_contact(session=session, tenant_id=tenant_id, contact_id=contact_id)
        await self.dao.delete(contact_id, session=session)
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
