from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.data_base.models import ContactCard, ContactLink
from api.schemas.contacts import ContactLinkCreate, ContactLinkUpdate


async def _ensure_contact_belongs_to_tenant(session: AsyncSession, tenant_id, contact_id: UUID) -> None:
    stmt = select(ContactCard).where(ContactCard.id == contact_id)
    if tenant_id is not None:
        stmt = stmt.where(ContactCard.tenant_id == tenant_id)
    result = await session.execute(stmt)
    contact = result.scalar_one_or_none()
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")


async def list_links_for_contact(
    session: AsyncSession,
    tenant_id,
    contact_id: UUID,
):
    # 404 если контакт не принадлежит тенанту — единая точка проверки с create/update/delete.
    await _ensure_contact_belongs_to_tenant(session, tenant_id, contact_id)
    stmt = select(ContactLink).where(
        or_(
            ContactLink.contact_id_a == contact_id,
            ContactLink.contact_id_b == contact_id,
        )
    )
    if tenant_id is not None:
        stmt = stmt.where(ContactLink.tenant_id == tenant_id)
    result = await session.execute(stmt)
    return result.scalars().all()


async def create_link_for_contact(
    session: AsyncSession,
    tenant_id,
    contact_id_a: UUID,
    payload: ContactLinkCreate,
):
    await _ensure_contact_belongs_to_tenant(session, tenant_id, contact_id_a)
    await _ensure_contact_belongs_to_tenant(session, tenant_id, payload.contact_id_b)

    data = payload.model_dump()
    is_directed = bool(data.get("is_directed", False))
    a_id, b_id = contact_id_a, data["contact_id_b"]
    # Для симметричных связей нормализуем порядок, чтобы uq_contact_links_pair_type
    # ловил дубль и при обратной перестановке (A-B и B-A — одна и та же дружба).
    if not is_directed and str(a_id) > str(b_id):
        a_id, b_id = b_id, a_id

    link = ContactLink(
        tenant_id=tenant_id,
        contact_id_a=a_id,
        contact_id_b=b_id,
        relationship_type=data["relationship_type"],
        context=data.get("context"),
        is_directed=is_directed,
    )
    session.add(link)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Link with this relationship type already exists between these contacts",
        )
    await session.refresh(link)
    return link


async def update_link_for_contact(
    session: AsyncSession,
    tenant_id,
    contact_id: UUID,
    link_id: UUID,
    payload: ContactLinkUpdate,
):
    stmt = select(ContactLink).where(ContactLink.id == link_id)
    if tenant_id is not None:
        stmt = stmt.where(ContactLink.tenant_id == tenant_id)
    stmt = stmt.where(
        or_(
            ContactLink.contact_id_a == contact_id,
            ContactLink.contact_id_b == contact_id,
        )
    )
    result = await session.execute(stmt)
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(link, key, value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Link with this relationship type already exists between these contacts",
        )
    await session.refresh(link)
    return link


async def delete_link_for_contact(
    session: AsyncSession,
    tenant_id,
    contact_id: UUID,
    link_id: UUID,
):
    stmt = select(ContactLink).where(ContactLink.id == link_id)
    if tenant_id is not None:
        stmt = stmt.where(ContactLink.tenant_id == tenant_id)
    stmt = stmt.where(
        or_(
            ContactLink.contact_id_a == contact_id,
            ContactLink.contact_id_b == contact_id,
        )
    )
    result = await session.execute(stmt)
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

    await session.delete(link)
    await session.commit()

