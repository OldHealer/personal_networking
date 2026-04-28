"""
Concierge-агент личной сети.

Три ветки по intent:
  birthdays  — дни рождения контактов в заданном окне
  promises   — сводка открытых обещаний (mine / theirs)
  matchmaker — поиск контакта под задачу (цикл enrich)
  unknown    — запрос уточнения у пользователя

Топология:
  START → route_intent
    → collect_birthdays → synthesize_report → END
    → collect_promises  → synthesize_report → END
    → build_shortlist   → enrich_context → synthesize_report → END
    → ask_clarification → END
  (любой узел при ошибке → format_error → END)
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal, NotRequired, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from settings import config as app_config
from utils.logger_loguru import get_logger

logger = get_logger()

_llm_instance: ChatOllama | None = None


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class ConciergeState(TypedDict):
    user_message: str

    intent: NotRequired[Literal["birthdays", "promises", "matchmaker", "unknown"]]
    time_window: NotRequired[int]       # дней для ДР-сценария
    criteria: NotRequired[dict]         # {q, relationship_type} для matchmaker

    shortlist: NotRequired[list[dict]]  # базовый список контактов из contacts.list
    snapshots: NotRequired[dict]        # {contact_id: full_context} после enrich

    tool_round: NotRequired[int]
    audit: NotRequired[list[str]]

    final_reply: NotRequired[str]
    status: NotRequired[Literal["ok", "error", "clarification"]]
    error_message: NotRequired[str]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConciergeAgentConfig:
    llm: Any
    mode: Literal["mcp", "local"]
    access_token: str | None = None
    session: Any | None = None
    tenant_id: Any | None = None
    max_enrich_contacts: int = 3  # сколько контактов обогащать полным контекстом


def _get_llm() -> ChatOllama:
    global _llm_instance
    if _llm_instance is None:
        cfg = app_config.agent
        _llm_instance = ChatOllama(
            model=cfg.ollama_model,
            temperature=cfg.ollama_temperature,
            num_predict=cfg.ollama_num_predict,
            base_url=cfg.ollama_base_url,
            timeout=cfg.ollama_timeout,
        )
    return _llm_instance


# ---------------------------------------------------------------------------
# Tool helpers (mode switch: local vs mcp)
# ---------------------------------------------------------------------------

async def _contacts_list(cfg: ConciergeAgentConfig, **kwargs) -> dict:
    if cfg.mode == "local":
        from agents.tools.contacts_tools import contacts_list
        return await contacts_list(session=cfg.session, tenant_id=cfg.tenant_id, **kwargs)
    from agents.mcp_app import mcp
    from fastmcp import Client
    async with Client(mcp) as client:
        result = await client.call_tool("contacts_list_tool", {"access_token": cfg.access_token, **kwargs})
    return result.data if not result.is_error else {}


async def _contacts_get(cfg: ConciergeAgentConfig, contact_id: str) -> dict:
    if cfg.mode == "local":
        from agents.tools.contacts_tools import contacts_get
        return await contacts_get(session=cfg.session, tenant_id=cfg.tenant_id, contact_id=contact_id)
    from agents.mcp_app import mcp
    from fastmcp import Client
    async with Client(mcp) as client:
        result = await client.call_tool("contacts_get_tool", {"access_token": cfg.access_token, "contact_id": contact_id})
    return result.data if not result.is_error else {}


async def _promises_list(cfg: ConciergeAgentConfig, open_only: bool = True, direction: str | None = None) -> dict:
    if cfg.mode == "local":
        from agents.tools.contacts_tools import promises_list
        return await promises_list(session=cfg.session, tenant_id=cfg.tenant_id, open_only=open_only, direction=direction)
    from agents.mcp_app import mcp
    from fastmcp import Client
    params: dict = {"access_token": cfg.access_token, "open_only": open_only}
    if direction:
        params["direction"] = direction
    async with Client(mcp) as client:
        result = await client.call_tool("promises_list_tool", params)
    return result.data if not result.is_error else {}


def _extract_json(text: str) -> dict:
    """Вытаскивает первый JSON-объект из текста LLM."""
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return {}


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

async def node_route_intent(state: ConciergeState, *, cfg: ConciergeAgentConfig) -> ConciergeState:
    """LLM классифицирует намерение и извлекает параметры."""
    system = SystemMessage(content=(
        "Ты — маршрутизатор запросов личного CRM-ассистента.\n"
        "Определи намерение. Допустимые значения intent:\n"
        "  birthdays  — вопросы о днях рождения контактов\n"
        "  promises   — вопросы об обещаниях и обязательствах\n"
        "  matchmaker — поиск контакта под задачу или критерий\n"
        "  unknown    — намерение неясно\n\n"
        "Верни ТОЛЬКО JSON без пояснений:\n"
        '{"intent":"...","confidence":0.0-1.0,'
        '"time_window":<число_дней_или_null>,'
        '"search_query":"<ключевые_слова_или_пустая_строка>",'
        '"relationship_type":"<тип_или_null>"}'
    ))
    human = HumanMessage(content=f"Запрос: {state['user_message']}")

    try:
        resp = await cfg.llm.ainvoke([system, human])
        parsed = _extract_json(getattr(resp, "content", "") or "")
    except Exception as e:
        state["status"] = "error"
        state["error_message"] = f"Ошибка LLM при классификации намерения: {e}"
        return state

    intent = parsed.get("intent", "unknown")
    confidence = float(parsed.get("confidence") or 0.0)
    if intent not in ("birthdays", "promises", "matchmaker") or confidence < 0.5:
        intent = "unknown"

    state["intent"] = intent  # type: ignore[typeddict-item]
    state["time_window"] = int(parsed.get("time_window") or 30)
    state["criteria"] = {
        "q": parsed.get("search_query") or "",
        "relationship_type": parsed.get("relationship_type"),
    }
    state.setdefault("audit", []).append(f"intent={intent} confidence={confidence:.2f}")
    return state


async def node_collect_birthdays(state: ConciergeState, *, cfg: ConciergeAgentConfig) -> ConciergeState:
    days = state.get("time_window", 30)
    try:
        result = await _contacts_list(cfg, has_birthday_soon=days, per_page=50)
        state["shortlist"] = result.get("items", [])
        state["tool_round"] = 1
        state.setdefault("audit", []).append(
            f"contacts_list(has_birthday_soon={days}) → {len(state['shortlist'])} контактов"
        )
    except Exception as e:
        state["status"] = "error"
        state["error_message"] = f"Ошибка получения контактов с ДР: {e}"
    return state


async def node_collect_promises(state: ConciergeState, *, cfg: ConciergeAgentConfig) -> ConciergeState:
    try:
        result = await _promises_list(cfg, open_only=True)
        state["snapshots"] = {"promises": result.get("items", [])}
        state["tool_round"] = 1
        state.setdefault("audit", []).append(
            f"promises_list(open=True) → {len(state['snapshots']['promises'])} обещаний"
        )
    except Exception as e:
        state["status"] = "error"
        state["error_message"] = f"Ошибка получения обещаний: {e}"
    return state


async def node_build_shortlist(state: ConciergeState, *, cfg: ConciergeAgentConfig) -> ConciergeState:
    criteria = state.get("criteria", {})
    try:
        result = await _contacts_list(
            cfg,
            q=criteria.get("q") or None,
            relationship_type=criteria.get("relationship_type"),
            per_page=50,
        )
        state["shortlist"] = result.get("items", [])
        state["tool_round"] = state.get("tool_round", 0) + 1
        state.setdefault("audit", []).append(
            f"contacts_list(q={criteria.get('q')!r}) → {len(state['shortlist'])} контактов"
        )
    except Exception as e:
        state["status"] = "error"
        state["error_message"] = f"Ошибка получения shortlist: {e}"
    return state


async def node_enrich_context(state: ConciergeState, *, cfg: ConciergeAgentConfig) -> ConciergeState:
    """Обогащает топ-K контактов полным контекстом (карточка + связи + встречи)."""
    shortlist = state.get("shortlist", [])
    snapshots: dict = state.get("snapshots", {})

    for contact in shortlist[:cfg.max_enrich_contacts]:
        cid = str(contact.get("id", ""))
        if not cid or cid in snapshots:
            continue
        try:
            full = await _contacts_get(cfg, contact_id=cid)
            snapshots[cid] = full
            state.setdefault("audit", []).append(f"contacts_get({cid[:8]}…)")
        except Exception as e:
            logger.warning(f"enrich_context: пропускаем {cid}: {e}")

    state["snapshots"] = snapshots
    state["tool_round"] = state.get("tool_round", 0) + 1
    return state


async def node_synthesize_report(state: ConciergeState, *, cfg: ConciergeAgentConfig) -> ConciergeState:
    """LLM формирует финальный отчёт по собранным данным."""
    intent = state.get("intent", "unknown")

    today = date.today().isoformat()

    if intent == "birthdays":
        contacts = state.get("shortlist", [])
        days = state.get("time_window", 30)
        if not contacts:
            state["final_reply"] = f"# Дни рождения\n\nВ ближайшие {days} дней дней рождений нет."
            state["status"] = "ok"
            return state
        system = SystemMessage(content=(
            f"Сегодня {today}.\n"
            "Составь краткий отчёт о предстоящих днях рождения контактов.\n"
            "Для каждого: имя, дата рождения, сколько дней осталось (считай от сегодняшней даты).\n"
            "Формат: markdown-список."
        ))
        human = HumanMessage(content=f"Контакты с ДР в ближайшие {days} дней:\n{contacts}")

    elif intent == "promises":
        items = (state.get("snapshots") or {}).get("promises", [])
        if not items:
            state["final_reply"] = "# Обещания\n\nОткрытых обещаний нет."
            state["status"] = "ok"
            return state
        mine = [p for p in items if p.get("direction") == "mine"]
        theirs = [p for p in items if p.get("direction") == "theirs"]
        other = [p for p in items if p.get("direction") not in ("mine", "theirs")]
        system = SystemMessage(content=(
            "Составь структурированный отчёт по обещаниям.\n"
            "Разделы: МОИ ОБЕЩАНИЯ, МНЕ ОБЕЩАЛИ, НЕЯСНО.\n"
            "Для каждого: текст и имя контакта. Формат: markdown."
        ))
        human = HumanMessage(content=(
            f"Мои обещания ({len(mine)}):\n{mine}\n\n"
            f"Мне обещали ({len(theirs)}):\n{theirs}\n\n"
            f"Неясно ({len(other)}):\n{other}"
        ))

    else:  # matchmaker
        shortlist = state.get("shortlist", [])
        snapshots = state.get("snapshots", {})
        query = (state.get("criteria") or {}).get("q", state.get("user_message", ""))
        if not shortlist:
            state["final_reply"] = "# Поиск контакта\n\nКонтакты не найдены."
            state["status"] = "ok"
            return state
        enriched = [
            snapshots[str(c["id"])]
            for c in shortlist[:cfg.max_enrich_contacts]
            if str(c.get("id", "")) in snapshots
        ]
        system = SystemMessage(content=(
            "Пользователь ищет контакт под задачу.\n"
            "Выбери топ-3 наиболее подходящих, объясни почему.\n"
            "Используй только факты из предоставленных данных.\n"
            "Формат: markdown, отдельный блок на каждого кандидата."
        ))
        human = HumanMessage(content=(
            f"Запрос: {query}\n\n"
            f"Все контакты (базовая информация):\n{shortlist}\n\n"
            f"Детальная информация по топ-{cfg.max_enrich_contacts}:\n{enriched}"
        ))

    try:
        resp = await cfg.llm.ainvoke([system, human])
        state["final_reply"] = getattr(resp, "content", "") or "—"
        state["status"] = "ok"
    except Exception as e:
        state["status"] = "error"
        state["error_message"] = f"Ошибка LLM при синтезе отчёта: {e}"
    return state


async def node_ask_clarification(state: ConciergeState) -> ConciergeState:
    state["final_reply"] = (
        "Уточните запрос:\n\n"
        "- **Дни рождения**: «кому скоро ДР?», «дни рождения на этой неделе»\n"
        "- **Обещания**: «что я обещал?», «кто мне должен?», «открытые обязательства»\n"
        "- **Найти контакт**: «кто поможет с X?», «найди коллегу из IT»"
    )
    state["status"] = "clarification"
    return state


async def node_format_error(state: ConciergeState) -> ConciergeState:
    state["final_reply"] = f"# Ошибка\n\n{state.get('error_message', 'Неизвестная ошибка')}"
    return state


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def build_concierge_graph(cfg: ConciergeAgentConfig):
    g: StateGraph = StateGraph(ConciergeState)

    async def _route(s):      return await node_route_intent(s, cfg=cfg)
    async def _birthdays(s):  return await node_collect_birthdays(s, cfg=cfg)
    async def _promises(s):   return await node_collect_promises(s, cfg=cfg)
    async def _shortlist(s):  return await node_build_shortlist(s, cfg=cfg)
    async def _enrich(s):     return await node_enrich_context(s, cfg=cfg)
    async def _synthesize(s): return await node_synthesize_report(s, cfg=cfg)

    g.add_node("route_intent",      _route)
    g.add_node("collect_birthdays", _birthdays)
    g.add_node("collect_promises",  _promises)
    g.add_node("build_shortlist",   _shortlist)
    g.add_node("enrich_context",    _enrich)
    g.add_node("synthesize_report", _synthesize)
    g.add_node("ask_clarification", node_ask_clarification)
    g.add_node("format_error",      node_format_error)

    def _err(s): return "format_error" if s.get("status") == "error" else None

    g.add_edge(START, "route_intent")

    g.add_conditional_edges("route_intent", lambda s: (
        "format_error" if s.get("status") == "error" else
        {"birthdays": "collect_birthdays", "promises": "collect_promises",
         "matchmaker": "build_shortlist"}.get(s.get("intent", ""), "ask_clarification")
    ))
    g.add_conditional_edges("collect_birthdays",
                            lambda s: "format_error" if s.get("status") == "error" else "synthesize_report")
    g.add_conditional_edges("collect_promises",
                            lambda s: "format_error" if s.get("status") == "error" else "synthesize_report")
    g.add_conditional_edges("build_shortlist",
                            lambda s: "format_error" if s.get("status") == "error" else "enrich_context")
    g.add_conditional_edges("enrich_context",
                            lambda s: "format_error" if s.get("status") == "error" else "synthesize_report")
    g.add_conditional_edges("synthesize_report",
                            lambda s: "format_error" if s.get("status") == "error" else END)
    g.add_edge("ask_clarification", END)
    g.add_edge("format_error", END)

    return g.compile()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def run_concierge_agent(
    *,
    message: str,
    access_token: str,
    session: Any | None = None,
    tenant_id: Any | None = None,
    llm: Any | None = None,
) -> ConciergeState:
    cfg = ConciergeAgentConfig(
        llm=llm or _get_llm(),
        mode=app_config.agent.mode,
        access_token=access_token,
        session=session,
        tenant_id=tenant_id,
    )
    graph = build_concierge_graph(cfg)
    state: ConciergeState = {"user_message": message}

    try:
        return await asyncio.wait_for(
            graph.ainvoke(state),
            timeout=app_config.agent.agent_total_timeout,
        )
    except asyncio.TimeoutError:
        return {
            "user_message": message,
            "status": "error",
            "error_message": f"Агент не завершился за {app_config.agent.agent_total_timeout} секунд.",
            "final_reply": f"# Ошибка\n\nАгент не завершился за {app_config.agent.agent_total_timeout} секунд.",
            "audit": ["timeout"],
        }
