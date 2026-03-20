"""
Реализация Multi‑step Task Agent "Подготовка к встрече с контактом" на LangGraph.

Технологии:
  - LangGraph: оркестрация шагов (узлов) в графе.
  - ChatOllama : LLM.

Как это работает:
  - FastAPI роут `/api/v1/agents/prepare-meeting` создает state, запускает граф и возвращает `PrepareMeetingResponse`.
"""

import os
from dataclasses import dataclass
from typing import Any, Literal, NotRequired, TypedDict

from fastmcp import Client
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

from agents.mcp_app import mcp
from agents.tools.contacts_tools import contacts_get
from utils.logger_loguru import get_logger

logger = get_logger()

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
    draft_message: NotRequired[str]


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

    # session/tenant_id нужны только в local‑режиме (tools используют сервисный слой напрямую)
    session: Any | None = None
    tenant_id: Any | None = None

    interactions_limit: int = 10


def build_default_ollama_llm() -> ChatOllama:
    """
    Фабрика LLM.

    Вынесено отдельно, чтобы:
      - не размазывать параметры по коду,
      - можно было легко подменять LLM в тестах/экспериментах.
    """

    # Важно для Docker/Compose:
    # - внутри контейнера `localhost` указывает на контейнер, а не на хост-машину
    # - если Ollama запущена на хосте, то в Docker обычно нужен `http://host.docker.internal:11434`
    # Поэтому base_url делаем настраиваемым через env.
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()

    return ChatOllama(
        model="qwen2.5:14b",
        temperature=0.7,
        num_predict=2048,
        base_url=base_url,
    )


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
        if config.session is None or config.tenant_id is None:
            state["status"] = "error"
            state["error_message"] = "LOCAL mode требует session и tenant_id."
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
            history = result.data if hasattr(result, "data") else result  # совместимость

    state["history"] = history  # type: ignore[assignment]
    logger.info(f"Результат узла (get_history) {state}")
    state_history = {'user_query': 'Поляков Антон Сергеевич',
                     'contact_id': '2500a066-a93c-4e82-b556-e3f37bd99fe9',
                     'history': {
                         'contact': {'id': '2500a066-a93c-4e82-b556-e3f37bd99fe9',
                                     'tenant_id': 'b32ec583-6791-408e-b709-a8deda5fe227',
                                     'full_name': 'Поляков Антон Сергеевич', 'address': None, 'phone': None,
                                     'email': None,
                                     'relationship_type': 'personal',
                                     'hobbies': ['Футбол - еженедельно на роторе катает в миньку'], 'interests': [],
                                     'family_status': 'Не женат', 'birthday': '1985-07-08',
                                     'ambitions': None,
                                     'created_at': '2026-03-13T19:22:34.555527Z',
                                     'updated_at': '2026-03-17T13:46:43.868415Z'},
                         'links': [{'id': '156e7ac2-1d30-4ba7-a61f-f288f52c2953',
                                    'tenant_id': 'b32ec583-6791-408e-b709-a8deda5fe227',
                                    'contact_id_a': '2500a066-a93c-4e82-b556-e3f37bd99fe9',
                                    'contact_id_b': '1255543c-7e55-4b75-a5b3-f25affce6229',
                                    'relationship_type': 'friend',
                                    'context': 'Познакомились в университете', 'is_directed': 0,
                                    'created_at': '2026-03-13T20:04:27.797271Z',
                                    'updated_at': '2026-03-13T20:04:27.797271Z'},
                                   {'id': 'fb007ffb-719a-4cc3-8506-ffafccee3812',
                                    'tenant_id': 'b32ec583-6791-408e-b709-a8deda5fe227',
                                    'contact_id_a': '383908a0-2320-4779-b111-3b1d4aa94b78',
                                    'contact_id_b': '2500a066-a93c-4e82-b556-e3f37bd99fe9',
                                    'relationship_type': 'other',
                                    'context': 'Родные братья', 'is_directed': 0,
                                    'created_at': '2026-03-13T20:13:10.754224Z',
                                    'updated_at': '2026-03-13T20:13:10.754224Z'}],
                         'interactions': [
                             {'id': '45ab22d6-d63a-494e-b329-587ae4cebd1e',
                              'contact_id': '2500a066-a93c-4e82-b556-e3f37bd99fe9',
                              'occurred_at': '2025-11-14T20:00:00Z', 'channel': 'Встреча в "Праге"',
                              'notes': 'Был Софронов А.В.',
                              'promises': [], 'mentions': [], 'created_at': '2026-03-13T20:01:37.019183Z',
                              'updated_at': '2026-03-13T20:01:37.019183Z'}
                         ]}}
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
    logger.info(f'state: {state}')
    logger.info(f'state: {type(state)}')

    history = state.get("history")
    logger.info(f'history: {history}')

    if not history:
        state["status"] = "error"
        state["error_message"] = "Нет history для summarize_history."
        logger.info("Нет history для summarize_history.")
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

    logger.info(f'human: {human}')
    try:
        resp = await config.llm.ainvoke([system, human])
        text = getattr(resp, "content", "") or ""
        logger.info(f'Результат работы LLM -> {resp}')
    except Exception as e:
        # Частая причина: Ollama недоступна по base_url (например, внутри Docker localhost не тот).
        # Вместо падения всего запроса возвращаем понятную ошибку в state.
        state["status"] = "error"
        state["error_message"] = (
            "Не удалось подключиться к Ollama (LLM). "
            "Проверьте, что Ollama запущена и OLLAMA_BASE_URL задан корректно. "
            f"Ошибка: {e!s}"
        )
        logger.info(state["error_message"])
        return state

    # Парсер "в лоб" (для обучения): режем по маркерам.
    def _extract(block: str) -> str:
        return block.strip() if block else ""

    profile = ""
    last_interactions = ""
    promises = ""
    risks = ""

    # максимально простой парсинг по заголовкам
    parts = text.split("PROFILE:")
    if len(parts) > 1:
        rest = parts[1]
        # делим по следующим маркерам
        def _split(marker: str, s: str) -> tuple[str, str]:
            if marker in s:
                a, b = s.split(marker, 1)
                return a, b
            return s, ""

        p1, rest2 = _split("LAST_INTERACTIONS:", rest)
        p2, rest3 = _split("PROMISES:", rest2)
        p3, rest4 = _split("RISKS:", rest3)
        profile = _extract(p1)
        last_interactions = _extract(p2)
        promises = _extract(p3)
        risks = _extract(rest4)

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
    на выходе — практические советы + follow-ups + черновик сообщения.
    """
    logger.info(f'Стартую узел генерации совета')
    summary = state.get("summary")
    history = state.get("history")

    if not summary or not history:
        state["status"] = "error"
        state["error_message"] = "Нет summary/history для generate_advice."
        logger.info(state["error_message"])
        return state

    user_query = state.get("user_query", "")

    system = SystemMessage(
        content=(
            "Ты — помощник по подготовке к встрече.\n"
            "Дай практичные советы.\n"
            "Формат ответа строго:\n"
            "TALKING_POINTS:\n<список>\n\n"
            "FOLLOWUPS:\n<список>\n\n"
            "DRAFT_MESSAGE:\n<черновик>\n"
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
            "Проверьте Ollama и OLLAMA_BASE_URL. "
            f"Ошибка: {e!s}"
        )
        return state

    # Такой же простой парсер по маркерам
    talking_points = ""
    followups = ""
    draft = ""

    parts = text.split("TALKING_POINTS:")
    if len(parts) > 1:
        rest = parts[1]
        if "FOLLOWUPS:" in rest:
            a, rest2 = rest.split("FOLLOWUPS:", 1)
            talking_points = a.strip()
            if "DRAFT_MESSAGE:" in rest2:
                b, c = rest2.split("DRAFT_MESSAGE:", 1)
                followups = b.strip()
                draft = c.strip()
            else:
                followups = rest2.strip()
        else:
            talking_points = rest.strip()

    state["advice"] = {
        "talking_points": talking_points or "—",
        "followups": followups or "—",
        "draft_message": draft or "",
    }
    return state


async def node_format_output(state: PrepareMeetingState) -> PrepareMeetingState:
    """
    Узел: format_output (детерминированный)

    Собираем итоговый markdown‑подобный текст, который удобно показать в UI.
    """

    history = state.get("history") or {}
    summary = state.get("summary") or {}
    advice = state.get("advice") or {}

    contact = history.get("contact") or {}
    name = contact.get("full_name") or "Контакт"

    output = (
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

    draft = advice.get("draft_message") or ""
    if draft.strip():
        output += "## Черновик сообщения\n" + draft.strip() + "\n"

    state["output"] = output
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

    Почему так:
    - LangGraph по умолчанию вызывает узлы как `node(state)`.
    - Нам важно держать учебный код простым и явно контролировать зависимости узлов.
    - Поэтому вместо передачи cfg через runnable-config мы используем closure.
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

    async def _format_output(state: PrepareMeetingState) -> PrepareMeetingState:
        return await node_format_output(state)

    # Узлы
    g.add_node("get_history", _get_history)
    g.add_node("summarize_history", _summarize_history)
    g.add_node("generate_advice", _generate_advice)
    g.add_node("format_output", _format_output)

    # Рёбра (последовательный pipeline)
    g.add_edge(START, "get_history")
    g.add_edge("get_history", "summarize_history")
    g.add_edge("summarize_history", "generate_advice")
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

    # Режим выбирается через ENV: TODO сделать через settings.config
    #   ROCKFILE_AGENT_MODE=mcp|local
    # По умолчанию используем mcp, считается что это каноничный вариант
    mode = os.getenv("ROCKFILE_AGENT_MODE", "mcp").strip().lower()
    if mode not in ("mcp", "local"):
        mode = "mcp"

    cfg = PrepareMeetingAgentConfig(
        llm=llm or build_default_ollama_llm(),
        mode=mode,  # type: ignore[arg-type]
        access_token=access_token,
        session=session,
        tenant_id=tenant_id,
    )

    # Собираем граф под конкретный cfg (closures)
    graph = build_prepare_meeting_graph(cfg)

    # initial state
    state: PrepareMeetingState = {"user_query": query or "", "contact_id": contact_id}

    # LangGraph позволяет передавать "extra" аргументы в узлы через kwargs.
    # Здесь мы явно пробрасываем session/tenant_id/config.
    # Узлы уже "замкнули" cfg, поэтому ainvoke вызываем без доп. конфигов
    result: PrepareMeetingState = await graph.ainvoke(state)
    return result

