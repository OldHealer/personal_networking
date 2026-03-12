from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.data_base.models import ContactCard
from api.schemas.contacts import ContactCardCreate, ContactCardUpdate


def _apply_tenant_filter(stmt, tenant_id):
    if tenant_id is None:
        return stmt
    return stmt.where(ContactCard.tenant_id == tenant_id)


async def list_contacts(
    session: AsyncSession,
    tenant_id,
    page: int,
    per_page: int,
    sort: str,
):
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
    return items, total


async def create_contact(
    session: AsyncSession,
    tenant_id,
    payload: ContactCardCreate,
):
    contact = ContactCard(**payload.model_dump())
    contact.tenant_id = tenant_id
    session.add(contact)
    await session.commit()
    await session.refresh(contact)
    return contact


async def get_contact(
    session: AsyncSession,
    tenant_id,
    contact_id: str,
):
    stmt = select(ContactCard).where(ContactCard.id == contact_id)
    stmt = _apply_tenant_filter(stmt, tenant_id)
    result = await session.execute(stmt)
    contact = result.scalar_one_or_none()
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact


async def update_contact(
    session: AsyncSession,
    tenant_id,
    contact_id: str,
    payload: ContactCardUpdate,
):
    contact = await get_contact(session=session, tenant_id=tenant_id, contact_id=contact_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(contact, key, value)
    await session.commit()
    await session.refresh(contact)
    return contact


async def delete_contact(
    session: AsyncSession,
    tenant_id,
    contact_id: str,
):
    contact = await get_contact(session=session, tenant_id=tenant_id, contact_id=contact_id)
    await session.delete(contact)
    await session.commit()
    return None
