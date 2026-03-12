from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.deps import CurrentUser, get_current_user
from api.data_base.base import get_db_session
from api.schemas.contacts import (
    ContactCardCreate,
    ContactCardListResponse,
    ContactCardResponse,
    ContactCardUpdate,
)
from api.services.contacts_service import (
    create_contact as create_contact_service,
    delete_contact as delete_contact_service,
    get_contact as get_contact_service,
    list_contacts as list_contacts_service,
    update_contact as update_contact_service,
)

contacts_router = APIRouter(prefix="/api/v1/contacts", tags=["Contacts"])


@contacts_router.get("", response_model=ContactCardListResponse, summary="Список контактов")
async def list_contacts(
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(20, ge=1, le=100, description="Размер страницы"),
    sort: str = Query("name", description="Сортировка: name|last_contact_at|created_at"),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    items, total = await list_contacts_service(
        session=session,
        tenant_id=current_user.db_user.tenant_id,
        page=page,
        per_page=per_page,
        sort=sort,
    )
    return ContactCardListResponse(items=items, total=total, page=page, per_page=per_page)


@contacts_router.post("", response_model=ContactCardResponse, summary="Создать контакт")
async def create_contact(
    payload: ContactCardCreate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    return await create_contact_service(
        session=session,
        tenant_id=current_user.db_user.tenant_id,
        payload=payload,
    )


@contacts_router.get("/{contact_id}", response_model=ContactCardResponse, summary="Контакт по ID")
async def get_contact(
    contact_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    return await get_contact_service(
        session=session,
        tenant_id=current_user.db_user.tenant_id,
        contact_id=contact_id,
    )


@contacts_router.patch("/{contact_id}", response_model=ContactCardResponse, summary="Обновить контакт")
async def update_contact(
    contact_id: str,
    payload: ContactCardUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    return await update_contact_service(
        session=session,
        tenant_id=current_user.db_user.tenant_id,
        contact_id=contact_id,
        payload=payload,
    )


@contacts_router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить контакт")
async def delete_contact(
    contact_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    return await delete_contact_service(
        session=session,
        tenant_id=current_user.db_user.tenant_id,
        contact_id=contact_id,
    )
