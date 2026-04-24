"""Сервисный слой для карточек контактов — обёртка над DAO с изоляцией по tenant_id."""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
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
    """ Централизованная логика работы с контактами. """

    def __init__(self, dao: BaseDAO):
        self.dao = dao

    async def list_contacts(self, session: AsyncSession, tenant_id, page: int, per_page: int, sort: str,
                             q: str | None = None, last_contact_before: int | None = None,
                             relationship_type: str | None = None, has_birthday_soon: int | None = None):
        """ Получение списка контактов с пагинацией, сортировкой, поиском и фильтрами. """
        last_interaction_subq = (
            select(
                ContactInteraction.contact_id.label("contact_id"),
                func.max(ContactInteraction.occurred_at).label("last_interaction_at"),
            )
            .group_by(ContactInteraction.contact_id)
            .subquery()
        )

        if sort == "last_contact_at":
            # Контакты без взаимодействий — в конец.
            sort_clause = last_interaction_subq.c.last_interaction_at.desc().nulls_last()
        elif sort == "created_at":
            sort_clause = ContactCard.created_at.desc()
        else:
            sort_clause = ContactCard.full_name.asc()

        base_stmt = _apply_tenant_filter(
            select(ContactCard, last_interaction_subq.c.last_interaction_at).outerjoin(
                last_interaction_subq,
                ContactCard.id == last_interaction_subq.c.contact_id,
            ),
            tenant_id,
        )
        count_stmt = _apply_tenant_filter(
            select(func.count(ContactCard.id)).select_from(ContactCard).outerjoin(
                last_interaction_subq,
                ContactCard.id == last_interaction_subq.c.contact_id,
            ),
            tenant_id,
        )

        if q and q.strip():
            pattern = f"%{q.strip()}%"
            q_filter = or_(
                ContactCard.full_name.ilike(pattern),
                ContactCard.email.ilike(pattern),
            )
            base_stmt = base_stmt.where(q_filter)
            count_stmt = count_stmt.where(q_filter)

        if last_contact_before is not None and last_contact_before > 0:
            threshold = datetime.now(timezone.utc) - timedelta(days=last_contact_before)
            # Нет взаимодействий — считаем от created_at; иначе от last_interaction_at.
            effective_ts = func.coalesce(last_interaction_subq.c.last_interaction_at, ContactCard.created_at)
            stale_filter = effective_ts < threshold
            base_stmt = base_stmt.where(stale_filter)
            count_stmt = count_stmt.where(stale_filter)

        if relationship_type:
            rel_filter = ContactCard.relationship_type == relationship_type
            base_stmt = base_stmt.where(rel_filter)
            count_stmt = count_stmt.where(rel_filter)

        if has_birthday_soon is not None and has_birthday_soon >= 0:
            # Кольцевая разница в днях через day-of-year — корректно обрабатывает конец года.
            doy_bd = func.extract("doy", ContactCard.birthday)
            doy_today = func.extract("doy", func.current_date())
            days_until = (doy_bd - doy_today + 366) % 366
            bd_filter = (ContactCard.birthday.isnot(None)) & (days_until <= has_birthday_soon)
            base_stmt = base_stmt.where(bd_filter)
            count_stmt = count_stmt.where(bd_filter)

        total = (await session.execute(count_stmt)).scalar_one()
        offset = (page - 1) * per_page
        result = await session.execute(
            base_stmt.order_by(sort_clause).offset(offset).limit(per_page)
        )
        rows = result.all()
        items = []
        for contact, last_interaction_at in rows:
            # Поле вычисляемое (не хранится в ContactCard), нужно для миникарточек.
            setattr(contact, "last_interaction_at", last_interaction_at)
            items.append(contact)

        return items, total


    async def get_contact(self, session: AsyncSession, tenant_id, contact_id: str):
        """ Получить контакт по ID с изоляцией по tenant_id. """
        stmt = _apply_tenant_filter(
            select(ContactCard).where(ContactCard.id == contact_id),
            tenant_id,
        )
        contact = (await session.execute(stmt)).scalar_one_or_none()
        if contact is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
        return contact


    async def create_contact(self, session: AsyncSession, tenant_id, payload: ContactCardCreate):
        """ Создать карточку контакта c безопасной подстановкой tenant_id.

        Если tenant_id у пользователя указывает на несуществующего арендатора,
        создаём такого арендатора автоматически.
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
        logger.info(f"Created contact {contact.full_name}")
        return contact


    async def update_contact(self, session: AsyncSession, tenant_id, contact_id: str, payload: ContactCardUpdate):
        """ Частичное обновление контакта с проверкой tenant. """
        await self.get_contact(session=session, tenant_id=tenant_id, contact_id=contact_id)
        data = payload.model_dump(exclude_unset=True)
        contact = await self.dao.update(contact_id, data, session=session)
        logger.info(f"Updated contact {contact.full_name}, updated {data}")
        return contact


    async def delete_contact(self, session: AsyncSession, tenant_id, contact_id: str):
        """Удалить контакт с проверкой tenant."""
        contact = await self.get_contact(session=session, tenant_id=tenant_id, contact_id=contact_id)
        await self.dao.delete(contact_id, session=session)
        logger.info(f"Deleted contact {contact.full_name}|{contact_id}")
        return None

    async def get_stats(self, session: AsyncSession, tenant_id) -> dict:
        """Статистика: всего контактов + разбивка по типу отношений."""
        stmt = _apply_tenant_filter(
            select(
                ContactCard.relationship_type,
                func.count(ContactCard.id).label("cnt"),
            ).group_by(ContactCard.relationship_type),
            tenant_id,
        )
        rows = (await session.execute(stmt)).all()
        by_type = {(r.relationship_type or "other"): r.cnt for r in rows}
        total = sum(by_type.values())
        return {"total": total, "by_type": by_type}


# Единственный экземпляр сервиса для приложения (удобно подменять в тестах)
contact_service = ContactService(contacts_dao)


# Публичный API для роутера (обратная совместимость)
async def list_contacts(session, tenant_id, page, per_page, sort, q=None, last_contact_before=None,
                        relationship_type=None, has_birthday_soon=None):
    return await contact_service.list_contacts(session=session, tenant_id=tenant_id, page=page,
                                               per_page=per_page, sort=sort, q=q,
                                               last_contact_before=last_contact_before,
                                               relationship_type=relationship_type,
                                               has_birthday_soon=has_birthday_soon)


async def create_contact(session, tenant_id, payload: ContactCardCreate):
    return await contact_service.create_contact(session=session, tenant_id=tenant_id, payload=payload)


async def get_contact(session, tenant_id, contact_id: str):
    return await contact_service.get_contact(session=session, tenant_id=tenant_id, contact_id=contact_id)


async def update_contact(session, tenant_id, contact_id: str, payload: ContactCardUpdate):
    return await contact_service.update_contact(session=session, tenant_id=tenant_id, contact_id=contact_id,
                                                payload=payload)


async def delete_contact(session, tenant_id, contact_id: str):
    return await contact_service.delete_contact(session=session, tenant_id=tenant_id, contact_id=contact_id)


async def get_stats(session, tenant_id) -> dict:
    return await contact_service.get_stats(session=session, tenant_id=tenant_id)
