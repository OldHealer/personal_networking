from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.deps import CurrentUser, get_current_user
from api.data_base.base import get_db_session
from api.schemas.contacts import (ContactInteractionCreate, ContactInteractionResponse, ContactInteractionUpdate,)
from api.services.interactions_service import (complete_promise_for_contact, create_interaction_for_contact, 
                                               delete_interaction_for_contact, list_interactions_for_contact, 
                                               update_interaction_for_contact,)


contact_interactions_router = APIRouter(prefix="/api/v1/contacts", tags=["Contact Interactions"])


@contact_interactions_router.get("/{contact_id}/interactions",
                                 response_model=list[ContactInteractionResponse],
                                 summary="Список взаимодействий контакта",)
async def list_contact_interactions(contact_id: UUID,
                                    current_user: CurrentUser = Depends(get_current_user),
                                    session: AsyncSession = Depends(get_db_session)):
    return await list_interactions_for_contact(session=session, tenant_id=current_user.db_user.tenant_id, 
                                               contact_id=contact_id,)


@contact_interactions_router.post(
    "/{contact_id}/interactions",
    response_model=ContactInteractionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить взаимодействие",
)
async def create_contact_interaction(
    contact_id: UUID,
    payload: ContactInteractionCreate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    return await create_interaction_for_contact(
        session=session,
        tenant_id=current_user.db_user.tenant_id,
        contact_id=contact_id,
        payload=payload,
    )


@contact_interactions_router.patch(
    "/{contact_id}/interactions/{interaction_id}",
    response_model=ContactInteractionResponse,
    summary="Обновить взаимодействие",
)
async def update_contact_interaction(
    contact_id: UUID,
    interaction_id: UUID,
    payload: ContactInteractionUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    return await update_interaction_for_contact(
        session=session,
        tenant_id=current_user.db_user.tenant_id,
        contact_id=contact_id,
        interaction_id=interaction_id,
        payload=payload,
    )


@contact_interactions_router.delete(
    "/{contact_id}/interactions/{interaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить взаимодействие",
)
async def delete_contact_interaction(
    contact_id: UUID,
    interaction_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    await delete_interaction_for_contact(
        session=session,
        tenant_id=current_user.db_user.tenant_id,
        contact_id=contact_id,
        interaction_id=interaction_id,
    )
    return None


@contact_interactions_router.post(
    "/{contact_id}/promises/{promise_id}/complete",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отметить обещание выполненным",
)
async def complete_promise(
    contact_id: UUID,
    promise_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    await complete_promise_for_contact(
        session=session,
        tenant_id=current_user.db_user.tenant_id,
        contact_id=contact_id,
        promise_id=promise_id,
    )
    return None

