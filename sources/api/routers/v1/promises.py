from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.deps import CurrentUser, get_current_user
from api.data_base.base import get_db_session
from api.schemas.contacts import PromiseListResponse, PromiseOut
from api.services.interactions_service import list_promises

promises_router = APIRouter(prefix="/api/v1/promises", tags=["Promises"])


@promises_router.get("", response_model=PromiseListResponse, summary="Список обещаний по всем контактам")
async def get_promises(
    open: bool = Query(True, description="Только открытые (completed_at is null)"),
    direction: str | None = Query(None, description="Фильтр по направлению: mine | theirs"),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.db_user.tenant_id
    items = await list_promises(session, tenant_id, open_only=open, direction=direction)
    return PromiseListResponse(
        items=[PromiseOut(**item) for item in items],
        total=len(items),
    )
