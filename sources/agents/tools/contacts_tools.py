"""
contacts_tools.py

В этом модуле лежат **детерминированные инструменты** (tools), которые использует LangGraph‑агент.

Ключевая идея для обучения:

1) Инструменты — это обычные python‑функции с понятным контрактом (вход/выход).
2) Агент НЕ делает SQL напрямую и НЕ "выдумывает" данные:
   - он вызывает tools,
   - получает реальные данные Rockfile,
   - и только после этого запускает LLM‑узлы (summarize / advice).

Эти же инструменты затем можно экспонировать через MCP‑server (FastMCP),
чтобы ими мог пользоваться внешний клиент/инспектор.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.services.contacts_service import get_contact as get_contact_service
from api.services.links_service import list_links_for_contact
from api.services.interactions_service import list_interactions_for_contact


async def contacts_get(
    *,
    session: AsyncSession,
    tenant_id: Any,
    contact_id: str,
    limit_interactions: int = 10,
) -> dict[str, Any]:
    """
    Tool: contacts.get

    Возвращает **нормализованный контекст** для агента:
    - contact: dict (поля карточки)
    - links: list[dict]
    - interactions: list[dict] (последние N)

    Почему не возвращаем "сырые" ORM-объекты:
    - агентные узлы (особенно LLM) должны получать простые JSON‑подобные структуры;
    - так легче логировать state, тестировать и сериализовать.
    """

    if not contact_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="contact_id is required")

    contact = await get_contact_service(
        session=session,
        contact_id=contact_id,
    )

    # links/interactions принимают UUID в типах, но python‑UUID валидируется при вызове роутера.
    # В сервисном слое они уже делают проверки принадлежности tenant.
    links = await list_links_for_contact(
        session=session,
        tenant_id=tenant_id,
        contact_id=contact.id,
    )
    interactions = await list_interactions_for_contact(
        session=session,
        tenant_id=tenant_id,
        contact_id=contact.id,
    )

    # Пытаемся получить dict из моделей.
    # В базе моделей у вас есть Base.model_to_dict(), поэтому используем его.
    contact_dict = contact.model_to_dict() if hasattr(contact, "model_to_dict") else {"id": str(contact.id)}
    links_dict = [l.model_to_dict() if hasattr(l, "model_to_dict") else {"id": str(l.id)} for l in links]
    interactions_dict = [
        i.model_to_dict() if hasattr(i, "model_to_dict") else {"id": str(i.id)} for i in interactions[:limit_interactions]
    ]

    return {
        "contact": contact_dict,
        "links": links_dict,
        "interactions": interactions_dict,
    }

