"""
mcp_app.py

Здесь лежит **каноническая MCP‑аппа** (FastMCP) с tool'ами Rockfile.

Ключевой принцип "по‑канону MCP":
  - LangGraph‑агент не трогает сервисы/БД напрямую.
  - Он вызывает MCP tool'ы.
  - MCP tool'ы — это "слой инструментов" (tool layer), который:
      1) принимает контекст (например, access_token),
      2) валидирует/авторизует пользователя,
      3) открывает DB session,
      4) читает/пишет данные через сервисный слой приложения.

Такой дизайн даёт:
  - одинаковые инструменты для агентов/внешних клиентов,
  - понятную границу ответственности,
  - удобную отладку tool'ов отдельно от LLM.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from sqlalchemy import select

from api.auth.keycloak_module import verify_jwt_token
from api.data_base.base import db
from api.data_base.models import AppUser
from agents.tools.contacts_tools import contacts_get


mcp = FastMCP("rockfile-mcp")


@mcp.tool
def ping() -> dict[str, str]:
    """Проверка доступности MCP‑server."""

    return {"status": "ok"}


async def _get_or_create_user(session, token_payload) -> AppUser:
    """
    Мини‑копия логики `api.auth.deps._get_or_create_user`.

    Почему не импортируем напрямую:
    - это приватная функция в deps;
    - в учебных целях проще иметь явную логику здесь и подробно её описать.
    """

    query = select(AppUser).where(AppUser.keycloak_sub == token_payload.sub)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    if user:
        return user

    user = AppUser(
        keycloak_sub=token_payload.sub,
        username=token_payload.preferred_username,
        email=token_payload.email,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@mcp.tool
async def contacts_get_tool(
    access_token: str,
    contact_id: str,
    interactions_limit: int = 10,
) -> dict[str, Any]:
    """
    MCP tool: contacts.get

    Вход:
      - access_token: JWT пользователя (как в Authorization Bearer)
      - contact_id: UUID контакта в Rockfile
      - interactions_limit: сколько последних взаимодействий вернуть

    Выход:
      - { contact, links, interactions }

    Внутри:
      1) валидируем токен (iss/aud/exp/подпись)
      2) получаем/создаём пользователя в локальной БД (AppUser)
      3) берём tenant_id пользователя
      4) читаем данные контакта через сервисный слой (contacts_get)
    """

    token_payload = await verify_jwt_token(access_token)

    async with db.session_factory() as session:
        db_user = await _get_or_create_user(session, token_payload)
        tenant_id = db_user.tenant_id

        return await contacts_get(
            session=session,
            tenant_id=tenant_id,
            contact_id=contact_id,
            limit_interactions=interactions_limit,
        )

