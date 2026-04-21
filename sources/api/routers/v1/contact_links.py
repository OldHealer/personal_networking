from uuid import UUID

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.deps import CurrentUser, get_current_user
from api.data_base.base import get_db_session
from api.schemas.contacts import (
    ContactLinkCreate,
    ContactLinkResponse,
    ContactLinkUpdate,
)
from api.services.links_service import (
    create_link_for_contact,
    delete_link_for_contact,
    list_links_for_contact,
    update_link_for_contact,
)


contact_links_router = APIRouter(
    prefix="/api/v1/contacts",
    tags=["Contact Links"],
)


@contact_links_router.get(
    "/{contact_id}/links",
    response_model=list[ContactLinkResponse],
    summary="Список связей контакта",
)
async def list_contact_links(
    contact_id: UUID = Path(..., description="ID контакта"),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    return await list_links_for_contact(
        session=session,
        tenant_id=current_user.db_user.tenant_id,
        contact_id=contact_id,
    )


@contact_links_router.post(
    "/{contact_id}/links",
    response_model=ContactLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить связь с другим контактом",
)
async def create_contact_link(
    contact_id: UUID,
    payload: ContactLinkCreate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    return await create_link_for_contact(
        session=session,
        tenant_id=current_user.db_user.tenant_id,
        contact_id_a=contact_id,
        payload=payload,
    )


@contact_links_router.patch(
    "/{contact_id}/links/{link_id}",
    response_model=ContactLinkResponse,
    summary="Обновить связь",
)
async def update_contact_link(
    contact_id: UUID,
    link_id: UUID,
    payload: ContactLinkUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    return await update_link_for_contact(
        session=session,
        tenant_id=current_user.db_user.tenant_id,
        contact_id=contact_id,
        link_id=link_id,
        payload=payload,
    )


@contact_links_router.delete(
    "/{contact_id}/links/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить связь",
)
async def delete_contact_link(
    contact_id: UUID,
    link_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    await delete_link_for_contact(
        session=session,
        tenant_id=current_user.db_user.tenant_id,
        contact_id=contact_id,
        link_id=link_id,
    )
    return None

