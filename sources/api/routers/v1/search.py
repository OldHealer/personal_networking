from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.deps import CurrentUser, get_current_user
from api.data_base.base import get_db_session
from api.schemas.search import SearchContactHit, SearchInteractionHit, SearchResponse
from api.services.search_service import search_contacts_and_interactions


search_router = APIRouter(prefix="/api/v1/search", tags=["Search"])


@search_router.get("", response_model=SearchResponse,
                   summary="Полнотекстовый поиск по контактам и взаимодействиям")
async def full_text_search(
    q: str = Query("", description="Строка поиска (russian text-search, поддерживает фразы в кавычках и OR)"),
    limit: int = Query(20, ge=1, le=100, description="Лимит результатов на каждую категорию"),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    contacts_rows, interactions_rows = await search_contacts_and_interactions(
        session=session,
        tenant_id=current_user.db_user.tenant_id,
        query=q,
        limit=limit,
    )
    contacts = [SearchContactHit(**row) for row in contacts_rows]
    interactions = [SearchInteractionHit(**row) for row in interactions_rows]
    return SearchResponse(
        query=q,
        total=len(contacts) + len(interactions),
        contacts=contacts,
        interactions=interactions,
    )
