"""
Реализация Multi‑step Task Agent "Подготовка к встрече с контактом" на LangGraph.

Технологии:
  - LangGraph: оркестрация шагов (узлов) в графе.
  - ChatOllama : LLM.

Как это работает:
  - FastAPI роут `/api/v1/agents/prepare-meeting` создает state, запускает граф и возвращает `PrepareMeetingResponse`.
"""

from dataclasses import dataclass
from typing import Any, Literal, NotRequired, TypedDict

from fastmcp import Client
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

from agents.mcp_app import mcp
from agents.tools.contacts_tools import contacts_get
from settings import config as app_config
from utils.logger_loguru import get_logger

logger = get_logger()

# кешированный LLM instance — не пересоздаём на каждый запрос
_llm_instance: ChatOllama | None = None

# ---------------------------------------------------------------------------
# 1) Тип состояния (state)
# ---------------------------------------------------------------------------

class PrepareMeetingHistory(TypedDict):
    """ Данные, загруженные из БД (JSON‑подобные структуры (dict/list), а не ORM‑объекты). """
    contact: dict
    links: list
    interactions: list


class PrepareMeetingSummary(TypedDict):
    """ Выжимка истории (LLM‑результат). """
    profile: str
    last_interactions: str
    promises: str
    risks: str


class PrepareMeetingAdvice(TypedDict):
    """ Советы (LLM‑результат). """
    talking_points: str
    followups: str


class PrepareMeetingState(TypedDict):
    """
    Состояние LangGraph.

    Этот объект мутирует по ходу выполнения узлов.
    Узлы должны:
      - читать только то, что им нужно,
      - записывать только те поля, за которые они отвечают,
      - при ошибке выставлять status/error_message и завершаться.
    """
    # входы
    user_query: str
    contact_id: str  # contact_id всегда приходит с фронта (выбираю из поиска)

    # результаты tools
    history: NotRequired[PrepareMeetingHistory]

    # результаты LLM
    summary: NotRequired[PrepareMeetingSummary]
    advice: NotRequired[PrepareMeetingAdvice]

    # финальный вывод
    output: NotRequired[str]

    # служебное
    status: NotRequired[Literal["ok", "not_found", "error"]]
    error_message: NotRequired[str]


# ---------------------------------------------------------------------------
# 2) Конфиг агента (LLM + параметры)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PrepareMeetingAgentConfig:
    """
    Конфигурация агента.

    Здесь удобно держать:
      - LLM объект (ChatOllama)
      - ограничения (сколько взаимодействий подтягивать)
      - другие параметры для обучения/экспериментов
    """
    llm: Any
    # Режим работы агента:
    # - "mcp": agent -> MCP tools -> сервисный слой/БД
    # - "local": agent -> tools напрямую (без MCP), внутри одного процесса FastAPI
    mode: Literal["mcp", "local"]

    # access_token нужен только в MCP‑режиме (MCP tool layer валидирует токен)
    access_token: str | None = None

    # session нужна только в local‑режиме; tenant_id нужен для изоляции list_links/interactions
    session: Any | None = None
    tenant_id: Any | None = None

    interactions_limit: int = 10


def build_default_ollama_llm() -> ChatOllama:
    """
    Фабрика LLM с кешированием instance.

    Вынесено отдельно, чтобы:
      - не размазывать параметры по коду,
      - можно было легко подменять LLM в тестах/экспериментах.
    """
    global _llm_instance
    if _llm_instance is None:
        agent_cfg = app_config.agent
        _llm_instance = ChatOllama(
            model=agent_cfg.ollama_model,
            temperature=agent_cfg.ollama_temperature,
            num_predict=agent_cfg.ollama_num_predict,
            base_url=agent_cfg.ollama_base_url,
        )
    return _llm_instance


# ---------------------------------------------------------------------------
# 3) Узлы графа (каждый — маленькая функция "делает одно")
# ---------------------------------------------------------------------------


async def node_get_history(state: PrepareMeetingState, *, config: PrepareMeetingAgentConfig) -> PrepareMeetingState:
    """
    Узел: get_history

    По‑канону MCP:
    - агент НЕ вызывает сервисы приложения напрямую,
    - вместо этого он вызывает MCP tool `contacts.get` через `fastmcp.Client`.

    Почему это полезно:
    - узел видит только "инструмент" и его контракт,
    - источник данных (БД/HTTP/другой сервис) скрыт за MCP‑tool.
    """

    contact_id = state.get("contact_id")
    if not contact_id:
        state["status"] = "error"
        state["error_message"] = "contact_id обязателен (должен приходить с фронта)."
        return state

    # --- MODE SWITCH ---
    # Здесь и происходит переключение режимов.
    # Обрати внимание: ниже мы НЕ меняем остальной граф.
    # Вся разница скрыта внутри одного узла `get_history`.

    if config.mode == "local":
        # LOCAL‑режим: обращаемся к сервисному слою напрямую через tool `contacts_get`.
        # Плюсы: быстро, просто, без транспорта MCP.
        # Минусы: tools не стандартизированы протоколом MCP.
        if config.session is None:
            state["status"] = "error"
            state["error_message"] = "LOCAL mode требует session."
            return state

        history = await contacts_get(
            session=config.session,
            tenant_id=config.tenant_id,
            contact_id=contact_id,
            limit_interactions=config.interactions_limit,
        )
    else:
        # MCP‑режим: обращаемся к данным через MCP tool layer.
        # Плюсы: строгая граница tool‑слоя; удобная интеграция с внешними клиентами.
        # Минусы: дополнительный слой абстракции/вызовов.
        if not config.access_token:
            state["status"] = "error"
            state["error_message"] = "MCP mode требует access_token."
            return state

        # Важно: Client может работать "in‑process" — если передать ему FastMCP instance.
        # Это позволяет использовать MCP‑контракты без отдельного процесса/stdio во время разработки.
        client = Client(mcp)
        async with client:
            result = await client.call_tool(
                "contacts_get_tool",
                {
                    "access_token": config.access_token,
                    "contact_id": contact_id,
                    "interactions_limit": config.interactions_limit,
                },
            )

        # FastMCP возвращает CallToolResult; .data содержит уже распарсенный dict
        if result.is_error:
            state["status"] = "error"
            state["error_message"] = f"MCP tool вернул ошибку: {result.data}"
            logger.error(state["error_message"])
            return state
        history = result.data

    state["history"] = history  # type: ignore[assignment]
    logger.info(f"get_history завершён: contact_id={contact_id}")
    return state


async def node_summarize_history(state: PrepareMeetingState, *, config: PrepareMeetingAgentConfig) -> PrepareMeetingState:
    """
    Узел: summarize_history (LLM)

    На входе — state.history (реальные данные из Rockfile),
    на выходе — короткая структурированная сводка.

    Важно:
    - LLM получает "сырой" контекст, но мы чётко задаём формат ответа.
    - Для обучения проще вернуть 4 текстовых поля.
    """
    history = state.get("history")
    if not history:
        state["status"] = "error"
        state["error_message"] = "Нет history для summarize_history."
        logger.error(state["error_message"])
        return state

    contact = history.get("contact", {})
    links = history.get("links", [])
    interactions = history.get("interactions", [])

    system = SystemMessage(
        content=(
            "Ты — помощник по подготовке к встречам.\n"
            "Твоя задача: сделать краткую и практичную сводку по контакту.\n"
            "Формат ответа строго:\n"
            "PROFILE:\n<текст>\n\n"
            "LAST_INTERACTIONS:\n<текст>\n\n"
            "PROMISES:\n<текст>\n\n"
            "RISKS:\n<текст>\n"
        )
    )
    human = HumanMessage(
        content=(
            "Данные контакта (JSON):\n"
            f"{contact}\n\n"
            "Связи (JSON list):\n"
            f"{links}\n\n"
            "Последние взаимодействия (JSON list):\n"
            f"{interactions}\n"
        )
    )

    try:
        resp = await config.llm.ainvoke([system, human])
        text = getattr(resp, "content", "") or ""
        logger.info(f"summarize_history: LLM ответил ({len(text)} символов)")
    except Exception as e:
        # Частая причина: Ollama недоступна по base_url (например, внутри Docker localhost не тот).
        # Вместо падения всего запроса возвращаем понятную ошибку в state.
        state["status"] = "error"
        state["error_message"] = (
            "Не удалось подключиться к Ollama (LLM). "
            "Проверьте, что Ollama запущена и AGENT__OLLAMA_BASE_URL задан корректно. "
            f"Ошибка: {e!s}"
        )
        logger.error(state["error_message"])
        return state

    # Парсер "в лоб": режем по маркерам.
    def _extract(block: str) -> str:
        return block.strip() if block else ""

    def _split(marker: str, s: str) -> tuple[str, str]:
        if marker in s:
            a, b = s.split(marker, 1)
            return a, b
        return s, ""

    profile = last_interactions = promises = risks = ""
    parts = text.split("PROFILE:")
    if len(parts) > 1:
        rest = parts[1]
        p1, rest2 = _split("LAST_INTERACTIONS:", rest)
        p2, rest3 = _split("PROMISES:", rest2)
        p3, rest4 = _split("RISKS:", rest3)
        profile = _extract(p1)
        last_interactions = _extract(p2)
        promises = _extract(p3)
        risks = _extract(rest4)

    # если LLM не дал структурированный ответ — кладём весь текст в profile
    if not any([profile, last_interactions, promises, risks]):
        profile = text.strip()

    state["summary"] = {
        "profile": profile or "—",
        "last_interactions": last_interactions or "—",
        "promises": promises or "—",
        "risks": risks or "—",
    }
    return state


async def node_generate_advice(state: PrepareMeetingState, *, config: PrepareMeetingAgentConfig) -> PrepareMeetingState:
    """
    Узел: generate_advice (LLM)

    На входе — state.summary + часть state.history,
    на выходе — практические советы + follow-ups.
    """
    summary = state.get("summary")
    history = state.get("history")

    if not summary or not history:
        state["status"] = "error"
        state["error_message"] = "Нет summary/history для generate_advice."
        logger.error(state["error_message"])
        return state

    user_query = state.get("user_query", "")

    system = SystemMessage(
        content=(
            "Ты — помощник по подготовке к встрече.\n"
            "Дай практичные советы.\n"
            "Формат ответа строго:\n"
            "TALKING_POINTS:\n<список>\n\n"
            "FOLLOWUPS:\n<список>\n"
        )
    )
    human = HumanMessage(
        content=(
            f"Запрос пользователя: {user_query}\n\n"
            f"Сводка:\n{summary}\n\n"
            f"Последние взаимодействия (JSON):\n{history.get('interactions', [])}\n"
        )
    )

    try:
        resp = await config.llm.ainvoke([system, human])
        text = getattr(resp, "content", "") or ""
    except Exception as e:
        state["status"] = "error"
        state["error_message"] = (
            "Не удалось подключиться к Ollama (LLM) на шаге генерации советов. "
            "Проверьте Ollama и AGENT__OLLAMA_BASE_URL. "
            f"Ошибка: {e!s}"
        )
        logger.error(state["error_message"])
        return state

    talking_points = followups = ""
    parts = text.split("TALKING_POINTS:")
    if len(parts) > 1:
        rest = parts[1]
        if "FOLLOWUPS:" in rest:
            a, rest2 = rest.split("FOLLOWUPS:", 1)
            talking_points = a.strip()
            followups = rest2.strip()
        else:
            talking_points = rest.strip()

    # если LLM не дал структурированный ответ — кладём весь текст в talking_points
    if not talking_points:
        talking_points = text.strip()

    state["advice"] = {
        "talking_points": talking_points or "—",
        "followups": followups or "—",
    }
    return state


async def node_format_output(state: PrepareMeetingState) -> PrepareMeetingState:
    """
    Узел: format_output (детерминированный)

    Собираем итоговый markdown‑подобный текст, который удобно показать в UI.
    Обрабатывает в том числе состояние ошибки — тогда выводит сообщение об ошибке.
    """

    if state.get("status") == "error":
        state["output"] = f"# Ошибка\n\n{state.get('error_message', 'Неизвестная ошибка')}"
        return state

    history = state.get("history") or {}
    summary = state.get("summary") or {}
    advice = state.get("advice") or {}

    contact = history.get("contact") or {}
    name = contact.get("full_name") or "Контакт"

    state["output"] = (
        f"# Подготовка к встрече с {name}\n\n"
        "## Кратко\n"
        f"{summary.get('profile', '—')}\n\n"
        "## Последние взаимодействия\n"
        f"{summary.get('last_interactions', '—')}\n\n"
        "## Обещания и ожидания\n"
        f"{summary.get('promises', '—')}\n\n"
        "## На что обратить внимание\n"
        f"{summary.get('risks', '—')}\n\n"
        "## О чём говорить\n"
        f"{advice.get('talking_points', '—')}\n\n"
        "## Follow‑up после встречи\n"
        f"{advice.get('followups', '—')}\n\n"
    )
    state["status"] = state.get("status") or "ok"
    return state


# ---------------------------------------------------------------------------
# 4) Сборка графа
# ---------------------------------------------------------------------------


def build_prepare_meeting_graph(cfg: PrepareMeetingAgentConfig) -> Any:
    """
    Создаём граф LangGraph.

    Важно: граф описывает *контроль потока* (что за чем идёт).
    Реальные параметры (LLM, access_token, лимиты, режим) мы "замыкаем" в узлах через cfg.

    При status=error на любом узле граф сразу переходит в format_output,
    минуя оставшиеся LLM‑узлы.
    """

    g: StateGraph[PrepareMeetingState] = StateGraph(PrepareMeetingState)

    # --- Обёртки-узлы (closures) ---
    # Каждый узел — функция от `state`, но внутри использует cfg.

    async def _get_history(state: PrepareMeetingState) -> PrepareMeetingState:
        return await node_get_history(state, config=cfg)

    async def _summarize_history(state: PrepareMeetingState) -> PrepareMeetingState:
        return await node_summarize_history(state, config=cfg)

    async def _generate_advice(state: PrepareMeetingState) -> PrepareMeetingState:
        return await node_generate_advice(state, config=cfg)

    # Узлы
    g.add_node("get_history", _get_history)
    g.add_node("summarize_history", _summarize_history)
    g.add_node("generate_advice", _generate_advice)
    g.add_node("format_output", node_format_output)

    # Рёбра: при ошибке сразу переходим в format_output, иначе — следующий узел
    g.add_edge(START, "get_history")
    g.add_conditional_edges(
        "get_history",
        lambda s: "format_output" if s.get("status") == "error" else "summarize_history",
    )
    g.add_conditional_edges(
        "summarize_history",
        lambda s: "format_output" if s.get("status") == "error" else "generate_advice",
    )
    g.add_edge("generate_advice", "format_output")
    g.add_edge("format_output", END)

    return g.compile()


# ---------------------------------------------------------------------------
# 5) High-level функция запуска агента (удобно вызывать из FastAPI)
# ---------------------------------------------------------------------------


async def run_prepare_meeting_agent(
    *,
    query: str,
    contact_id: str,
    access_token: str,
    session: Any | None = None,
    tenant_id: Any | None = None,
    llm: Any | None = None,
) -> PrepareMeetingState:
    """
    Запуск агента.

    Входы:
      - query: текстовый запрос пользователя
      - contact_id: ID контакта (UI выбирает из списка, бэкенд НЕ делает поиск)
      - access_token: JWT пользователя (нужен MCP tool layer для авторизации)
      - llm: опционально для DI (dependency injection). Если None — создаём ChatOllama.

    Выход:
      - финальный state, где `output` содержит готовый текст
      - `summary/advice` — структурированные блоки для UI
    """

    cfg = PrepareMeetingAgentConfig(
        llm=llm or build_default_ollama_llm(),
        mode=app_config.agent.mode,
        access_token=access_token,
        session=session,
        tenant_id=tenant_id,
    )

    graph = build_prepare_meeting_graph(cfg)
    state: PrepareMeetingState = {"user_query": query or "", "contact_id": contact_id}
    return await graph.ainvoke(state)
