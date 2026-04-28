from fastapi import APIRouter, Depends, HTTPException, Security, status

from api.auth.deps import CurrentUser, get_current_user, oauth2_scheme
from api.data_base.base import get_db_session
from api.schemas.agents import (PrepareMeetingRequest, PrepareMeetingResponse,
                                ConciergeRequest, ConciergeResponse)
from utils.logger_loguru import get_logger
from agents.prepare_meeting_agent import run_prepare_meeting_agent
from agents.concierge_agent import run_concierge_agent

logger = get_logger()
agents_router = APIRouter(prefix="/api/v1/agents", tags=["AI Agents"])


@agents_router.post(
    "/prepare-meeting",
    response_model=PrepareMeetingResponse,
    status_code=status.HTTP_200_OK,
    summary="Подготовить пользователя к встрече с контактом (multi‑step агент)",
)
async def prepare_meeting(
    payload: PrepareMeetingRequest,
    current_user: CurrentUser = Depends(get_current_user),
    token_str: str = Security(oauth2_scheme),
    session=Depends(get_db_session),
) -> PrepareMeetingResponse:
    """
    Multi‑step Task Agent: подготовка ко встрече с контактом.

    Эндпоинт является слоем над LangGraph‑агентом.

    Что происходит внутри (реальная логика):
    1) `get_history`       — через MCP tool `contacts.get` загружаем contact/links/interactions.
    2) `summarize_history` — LLM (ChatOllama) делает сводку по реальному контексту.
    3) `generate_advice`   — LLM генерирует советы и follow‑up.
    4) `format_output`     — детерминированно собираем текст для UI.

    Все данные берутся из Rockfile (не "галлюцинируются"), LLM используется только для
    сжатия/советов на основе реального контекста.
    """

    # Запускаем LangGraph‑агента.
    # Примечание: внутри агента есть переключатель режимов через ENV `ROCKFILE_AGENT_MODE`:
    # - mcp  (по умолчанию): доступ к данным через MCP tools
    # - local: прямой вызов tools через сервисный слой/БД
    logger.info(f'Запускаем агента подготовки встречи {payload}')

    result_state = await run_prepare_meeting_agent(query=payload.query or "",
                                                   contact_id=payload.contact_id,
                                                   access_token=token_str,
                                                   session=session,
                                                   tenant_id=current_user.db_user.tenant_id,)

    logger.info(f'Результат подготовки встречи {result_state}')

    status_value = result_state.get("status", "ok")
    if status_value != "ok":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if status_value == "not_found" else status.HTTP_400_BAD_REQUEST,
            detail=result_state.get("error_message", "Agent failed"),
        )

    history = result_state.get("history") or {}
    contact = history.get("contact") or {}
    contact_name = str(contact.get("full_name") or contact.get("email") or "Контакт")

    summary = result_state.get("summary") or {}
    advice = result_state.get("advice") or {}

    return PrepareMeetingResponse(  # type: ignore[return-value]
        contact_id=str(result_state.get("contact_id") or ""),
        contact_name=contact_name,
        summary=summary,  # pydantic примет dict, если совпадают поля
        advice=advice,    # pydantic примет dict, если совпадают поля
        raw_markdown=str(result_state.get("output") or ""),
    )


@agents_router.post(
    "/concierge",
    response_model=ConciergeResponse,
    status_code=status.HTTP_200_OK,
    summary="Concierge-агент: ДР, обещания, поиск контакта",
)
async def concierge(
    payload: ConciergeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    token_str: str = Security(oauth2_scheme),
    session=Depends(get_db_session),
) -> ConciergeResponse:
    """
    Мультисценарный агент с ветвлением по намерению:
    - **birthdays** — дни рождения контактов в заданном окне
    - **promises** — сводка открытых обещаний (mine / theirs)
    - **matchmaker** — поиск контакта под задачу
    - **unknown** — запрос уточнения
    """
    logger.info(f"Concierge запрос: {payload.message!r}")

    result = await run_concierge_agent(
        message=payload.message,
        access_token=token_str,
        session=session,
        tenant_id=current_user.db_user.tenant_id,
    )

    logger.info(f"Concierge результат: intent={result.get('intent')} status={result.get('status')}")

    return ConciergeResponse(
        intent=str(result.get("intent") or "unknown"),
        final_reply=str(result.get("final_reply") or ""),
        audit=list(result.get("audit") or []),
        status=str(result.get("status") or "ok"),
    )
