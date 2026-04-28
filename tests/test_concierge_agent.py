"""Тесты Concierge-агента.

Структура:
  - Юнит-тесты узлов графа (мок LLM + мок tool-helpers).
  - Интеграционный тест HTTP-эндпоинта (мок run_concierge_agent).
"""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from agents.concierge_agent import (
    ConciergeAgentConfig,
    node_ask_clarification,
    node_collect_birthdays,
    node_collect_promises,
    node_route_intent,
    node_synthesize_report,
    build_concierge_graph,
)


# ---------------------------------------------------------------------------
# Вспомогательные фабрики
# ---------------------------------------------------------------------------

def _llm_returning(json_dict: dict):
    """Мок LLM, возвращающий JSON-объект в поле content."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=SimpleNamespace(content=json.dumps(json_dict)))
    return llm


def _cfg(llm=None, **kwargs):
    return ConciergeAgentConfig(
        llm=llm or MagicMock(),
        mode="local",
        session=MagicMock(),
        tenant_id=uuid4(),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# node_route_intent
# ---------------------------------------------------------------------------

async def test_route_intent_birthdays():
    llm = _llm_returning({"intent": "birthdays", "confidence": 0.9, "time_window": 14})
    state = await node_route_intent({"user_message": "кому скоро ДР?"}, cfg=_cfg(llm))

    assert state["intent"] == "birthdays"
    assert state["time_window"] == 14
    assert any("intent=birthdays" in a for a in state["audit"])


async def test_route_intent_promises():
    llm = _llm_returning({"intent": "promises", "confidence": 0.85, "time_window": None})
    state = await node_route_intent({"user_message": "что я обещал?"}, cfg=_cfg(llm))

    assert state["intent"] == "promises"


async def test_route_intent_matchmaker():
    llm = _llm_returning({
        "intent": "matchmaker", "confidence": 0.8,
        "search_query": "инвестор", "relationship_type": None,
    })
    state = await node_route_intent({"user_message": "найди инвестора"}, cfg=_cfg(llm))

    assert state["intent"] == "matchmaker"
    assert state["criteria"]["q"] == "инвестор"


async def test_route_intent_low_confidence_becomes_unknown():
    llm = _llm_returning({"intent": "birthdays", "confidence": 0.3})
    state = await node_route_intent({"user_message": "хм"}, cfg=_cfg(llm))

    assert state["intent"] == "unknown"


async def test_route_intent_llm_error_sets_error_status():
    llm = MagicMock()
    llm.ainvoke = AsyncMock(side_effect=RuntimeError("ollama down"))
    state = await node_route_intent({"user_message": "тест"}, cfg=_cfg(llm))

    assert state["status"] == "error"
    assert "ollama down" in state["error_message"]


# ---------------------------------------------------------------------------
# node_collect_birthdays
# ---------------------------------------------------------------------------

async def test_collect_birthdays_populates_shortlist():
    contacts = [{"id": str(uuid4()), "full_name": "Иван", "date_of_birth": "1990-05-10"}]
    cfg = _cfg()
    with patch("agents.concierge_agent._contacts_list", new=AsyncMock(
        return_value={"items": contacts, "total": 1}
    )):
        state = await node_collect_birthdays(
            {"user_message": "ДР?", "intent": "birthdays", "time_window": 30}, cfg=cfg
        )

    assert state["shortlist"] == contacts
    assert state["tool_round"] == 1
    assert any("contacts_list" in a for a in state["audit"])


async def test_collect_birthdays_tool_error_sets_error_status():
    cfg = _cfg()
    with patch("agents.concierge_agent._contacts_list", new=AsyncMock(
        side_effect=RuntimeError("db error")
    )):
        state = await node_collect_birthdays(
            {"user_message": "ДР?", "intent": "birthdays", "time_window": 7}, cfg=cfg
        )

    assert state["status"] == "error"


# ---------------------------------------------------------------------------
# node_collect_promises
# ---------------------------------------------------------------------------

async def test_collect_promises_populates_snapshots():
    promises = [{"text": "позвонить", "direction": "mine", "contact_name": "Мария"}]
    cfg = _cfg()
    with patch("agents.concierge_agent._promises_list", new=AsyncMock(
        return_value={"items": promises, "total": 1}
    )):
        state = await node_collect_promises(
            {"user_message": "обещания?", "intent": "promises"}, cfg=cfg
        )

    assert state["snapshots"]["promises"] == promises
    assert state["tool_round"] == 1


# ---------------------------------------------------------------------------
# node_synthesize_report
# ---------------------------------------------------------------------------

async def test_synthesize_report_birthdays_empty_no_llm_call():
    llm = _llm_returning({})
    state = await node_synthesize_report(
        {"user_message": "", "intent": "birthdays", "shortlist": [], "time_window": 30},
        cfg=_cfg(llm),
    )

    assert state["status"] == "ok"
    assert "нет" in state["final_reply"].lower()
    llm.ainvoke.assert_not_called()


async def test_synthesize_report_promises_empty_no_llm_call():
    llm = _llm_returning({})
    state = await node_synthesize_report(
        {"user_message": "", "intent": "promises", "snapshots": {"promises": []}},
        cfg=_cfg(llm),
    )

    assert state["status"] == "ok"
    assert "нет" in state["final_reply"].lower()
    llm.ainvoke.assert_not_called()


async def test_synthesize_report_birthdays_calls_llm():
    llm = _llm_returning({})
    llm.ainvoke = AsyncMock(return_value=SimpleNamespace(content="# ДР\n- Иван: 5 мая"))
    contacts = [{"full_name": "Иван", "date_of_birth": "1990-05-05"}]
    state = await node_synthesize_report(
        {"user_message": "", "intent": "birthdays", "shortlist": contacts, "time_window": 14},
        cfg=_cfg(llm),
    )

    assert state["status"] == "ok"
    assert "Иван" in state["final_reply"]
    llm.ainvoke.assert_called_once()


async def test_synthesize_report_matchmaker_empty_no_llm_call():
    llm = _llm_returning({})
    state = await node_synthesize_report(
        {"user_message": "найди", "intent": "matchmaker", "shortlist": [],
         "snapshots": {}, "criteria": {"q": "инвестор"}},
        cfg=_cfg(llm),
    )

    assert state["status"] == "ok"
    assert "не найдены" in state["final_reply"].lower()
    llm.ainvoke.assert_not_called()


# ---------------------------------------------------------------------------
# node_ask_clarification
# ---------------------------------------------------------------------------

async def test_ask_clarification_returns_clarification_status():
    state = await node_ask_clarification({"user_message": "ладно"})

    assert state["status"] == "clarification"
    assert "ДР" in state["final_reply"] or "дни рождения" in state["final_reply"].lower()


# ---------------------------------------------------------------------------
# Полный граф
# ---------------------------------------------------------------------------

async def test_full_graph_birthdays_flow():
    llm = MagicMock()
    llm.ainvoke = AsyncMock(side_effect=[
        SimpleNamespace(content=json.dumps({"intent": "birthdays", "confidence": 0.9, "time_window": 7})),
        SimpleNamespace(content="# ДР\n- Наиля: 15 мая"),
    ])
    contacts = [{"id": str(uuid4()), "full_name": "Наиля", "date_of_birth": "1991-05-15"}]
    cfg = _cfg(llm)

    with patch("agents.concierge_agent._contacts_list", new=AsyncMock(
        return_value={"items": contacts, "total": 1}
    )):
        graph = build_concierge_graph(cfg)
        result = await graph.ainvoke({"user_message": "кому ДР на этой неделе?"})

    assert result["intent"] == "birthdays"
    assert result["status"] == "ok"
    assert result["final_reply"]


async def test_full_graph_unknown_intent_goes_to_clarification():
    llm = _llm_returning({"intent": "unknown", "confidence": 0.2})
    cfg = _cfg(llm)

    graph = build_concierge_graph(cfg)
    result = await graph.ainvoke({"user_message": "..."})

    assert result["intent"] == "unknown"
    assert result["status"] == "clarification"


async def test_full_graph_promises_flow():
    llm = MagicMock()
    llm.ainvoke = AsyncMock(side_effect=[
        SimpleNamespace(content=json.dumps({"intent": "promises", "confidence": 0.9})),
        SimpleNamespace(content="# Обещания\n- позвонить Ивану"),
    ])
    promises = [{"text": "позвонить Ивану", "direction": "mine", "contact_name": "Иван"}]
    cfg = _cfg(llm)

    with patch("agents.concierge_agent._promises_list", new=AsyncMock(
        return_value={"items": promises, "total": 1}
    )):
        graph = build_concierge_graph(cfg)
        result = await graph.ainvoke({"user_message": "что я обещал?"})

    assert result["intent"] == "promises"
    assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# HTTP-эндпоинт POST /api/v1/agents/concierge
# ---------------------------------------------------------------------------

_AUTH = {"Authorization": "Bearer test-token"}


async def test_concierge_endpoint_returns_200(client):
    mock_result = {
        "intent": "birthdays",
        "final_reply": "# ДР\n- Иван: 5 мая",
        "audit": ["intent=birthdays confidence=0.90"],
        "status": "ok",
    }
    with patch("api.routers.v1.agents.run_concierge_agent", new=AsyncMock(return_value=mock_result)):
        r = await client.post("/api/v1/agents/concierge", json={"message": "кому ДР?"}, headers=_AUTH)

    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "birthdays"
    assert body["status"] == "ok"
    assert body["final_reply"]


async def test_concierge_endpoint_empty_message_returns_422(client):
    r = await client.post("/api/v1/agents/concierge", json={"message": ""}, headers=_AUTH)
    assert r.status_code == 422


async def test_concierge_endpoint_unauthenticated_returns_401(unauth_client):
    r = await unauth_client.post("/api/v1/agents/concierge", json={"message": "тест"})
    assert r.status_code in (401, 403)
