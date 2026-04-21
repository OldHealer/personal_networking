from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.data_base.base import interactions_dao
from api.data_base.models import ContactCard, ContactInteraction
from api.schemas.contacts import ContactInteractionCreate, ContactInteractionUpdate


async def _get_contact_for_tenant(session: AsyncSession, tenant_id, contact_id: UUID) -> ContactCard:
    stmt = select(ContactCard).where(ContactCard.id == contact_id)
    if tenant_id is not None:
        stmt = stmt.where(ContactCard.tenant_id == tenant_id)
    result = await session.execute(stmt)
    contact = result.scalar_one_or_none()
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact


async def _rebuild_promises_for_contact(session: AsyncSession, contact: ContactCard) -> None:
    """Агрегирует обещания по всем взаимодействиям в ContactCard.promises."""
    stmt = select(ContactInteraction).where(ContactInteraction.contact_id == contact.id).order_by(
        ContactInteraction.occurred_at.desc()
    )
    result = await session.execute(stmt)
    interactions = result.scalars().all()

    aggregated: list[dict] = []
    for interaction in interactions:
        for raw in interaction.promises or []:
            item = dict(raw) if isinstance(raw, dict) else {"text": str(raw)}
            if "id" not in item:
                item["id"] = str(uuid4())
            item.setdefault("interaction_id", str(interaction.id))
            item.setdefault("completed_at", None)
            aggregated.append(item)

    contact.promises = aggregated
    await session.commit()


async def list_interactions_for_contact(
    session: AsyncSession,
    tenant_id,
    contact_id: UUID,
):
    await _get_contact_for_tenant(session, tenant_id, contact_id)
    stmt = (
        select(ContactInteraction)
        .where(ContactInteraction.contact_id == contact_id)
        .order_by(ContactInteraction.occurred_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def create_interaction_for_contact(
    session: AsyncSession,
    tenant_id,
    contact_id: UUID,
    payload: ContactInteractionCreate,
):
    contact = await _get_contact_for_tenant(session, tenant_id, contact_id)

    data = payload.model_dump()
    data["contact_id"] = contact_id

    interaction = await interactions_dao.create(data=data, session=session)



    # Агрегируем promises
    await _rebuild_promises_for_contact(session, contact)

    await session.refresh(interaction)
    return interaction


async def update_interaction_for_contact(
    session: AsyncSession,
    tenant_id,
    contact_id: UUID,
    interaction_id: UUID,
    payload: ContactInteractionUpdate,
):
    await _get_contact_for_tenant(session, tenant_id, contact_id)

    stmt = select(ContactInteraction).where(
        ContactInteraction.id == interaction_id,
        ContactInteraction.contact_id == contact_id,
    )
    result = await session.execute(stmt)
    interaction = result.scalar_one_or_none()
    if interaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interaction not found")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(interaction, key, value)
    await session.commit()

    # Пересчитываем promises
    contact = await _get_contact_for_tenant(session, tenant_id, contact_id)

    await _rebuild_promises_for_contact(session, contact)
    await session.refresh(interaction)
    return interaction


async def delete_interaction_for_contact(
    session: AsyncSession,
    tenant_id,
    contact_id: UUID,
    interaction_id: UUID,
):
    contact = await _get_contact_for_tenant(session, tenant_id, contact_id)

    stmt = select(ContactInteraction).where(
        ContactInteraction.id == interaction_id,
        ContactInteraction.contact_id == contact_id,
    )
    result = await session.execute(stmt)
    interaction = result.scalar_one_or_none()
    if interaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interaction not found")

    await session.delete(interaction)
    await session.commit()

    # Пересчитываем promises
    await _rebuild_promises_for_contact(session, contact)


async def complete_promise_for_contact(
    session: AsyncSession,
    tenant_id,
    contact_id: UUID,
    promise_id: UUID,
):
    contact = await _get_contact_for_tenant(session, tenant_id, contact_id)

    # Обновляем агрегированное обещание в карточке
    found = False
    now = datetime.now(timezone.utc)
    updated_promises: list[dict] = []
    for raw in contact.promises or []:
        item = dict(raw) if isinstance(raw, dict) else {"text": str(raw)}
        if str(item.get("id")) == str(promise_id):
            item["completed_at"] = now.isoformat()
            found = True
        updated_promises.append(item)

    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promise not found")

    contact.promises = updated_promises
    await session.commit()

    # Опционально: обновляем то же самое в Interaction.promises
    for item in updated_promises:
        if str(item.get("id")) == str(promise_id):
            interaction_id = item.get("interaction_id")
            if not interaction_id:
                break
            stmt = select(ContactInteraction).where(
                ContactInteraction.id == UUID(str(interaction_id)),
                ContactInteraction.contact_id == contact_id,
            )
            result = await session.execute(stmt)
            interaction = result.scalar_one_or_none()
            if interaction is None:
                break

            new_promises: list[dict] = []
            for raw_p in interaction.promises or []:
                p = dict(raw_p) if isinstance(raw_p, dict) else {"text": str(raw_p)}
                if str(p.get("id")) == str(promise_id):
                    p["completed_at"] = now.isoformat()
                new_promises.append(p)
            interaction.promises = new_promises
            await session.commit()
            break

