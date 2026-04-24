from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
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
    link = ContactLink(
        tenant_id=tenant_id,
        contact_id_a=contact_id_a,
        contact_id_b=data["contact_id_b"],
        relationship_type=data["relationship_type"],
        context=data.get("context"),
        is_directed=bool(data.get("is_directed", False)),
    )
    session.add(link)
    await session.commit()
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
    await session.commit()
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

