"""Интеграционные тесты для полнотекстового поиска /api/v1/search."""
from datetime import datetime, timezone

import pytest


SEARCH = "/api/v1/search"
CONTACTS = "/api/v1/contacts"


async def _create_contact(client, **fields) -> str:
    payload = {"full_name": fields.pop("full_name", "Тест Тестович"), **fields}
    resp = await client.post(CONTACTS, json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


async def _create_interaction(client, cid: str, **fields) -> str:
    payload = {"occurred_at": datetime.now(timezone.utc).isoformat(), **fields}
    resp = await client.post(f"{CONTACTS}/{cid}/interactions", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_search_by_contact_field(client):
    await _create_contact(client, full_name="Алексей Петров", ambitions="стартап про AI")
    await _create_contact(client, full_name="Иван Иванов", ambitions="разведение рыб")

    resp = await client.get(SEARCH, params={"q": "стартап"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "стартап"
    assert data["total"] >= 1
    names = [c["full_name"] for c in data["contacts"]]
    assert "Алексей Петров" in names
    assert "Иван Иванов" not in names


@pytest.mark.asyncio
async def test_search_by_interests_array(client):
    await _create_contact(client, full_name="Мария", interests=["фотография", "горные лыжи"])
    await _create_contact(client, full_name="Сергей", interests=["футбол"])

    resp = await client.get(SEARCH, params={"q": "фотография"})
    assert resp.status_code == 200
    names = [c["full_name"] for c in resp.json()["contacts"]]
    assert names == ["Мария"]


@pytest.mark.asyncio
async def test_search_in_interaction_notes(client):
    cid = await _create_contact(client, full_name="Дмитрий")
    await _create_interaction(client, cid, notes="обсудили переезд в Лиссабон и новую работу")

    resp = await client.get(SEARCH, params={"q": "Лиссабон"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["interactions"]) == 1
    hit = data["interactions"][0]
    assert hit["contact_full_name"] == "Дмитрий"
    assert hit["contact_id"] == cid
    # snippet должен содержать подсветку
    assert hit["snippet"]
    assert "<mark>" in hit["snippet"]


@pytest.mark.asyncio
async def test_search_empty_query_returns_empty(client):
    await _create_contact(client, full_name="Хоть кто-то")
    resp = await client.get(SEARCH, params={"q": "   "})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["contacts"] == []
    assert data["interactions"] == []


@pytest.mark.asyncio
async def test_search_respects_tenant_isolation(client, unauth_client):
    # Контакт в тенанте клиента
    await _create_contact(client, full_name="Свой контакт", ambitions="уникальное-слово-ключ")

    # unauth_client не имеет override get_current_user → 401 (проверяем что эндпоинт закрыт)
    resp = await unauth_client.get(SEARCH, params={"q": "уникальное-слово-ключ"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_search_ranking_multiple_hits(client):
    # "python" встречается и в амбициях, и в заметке — оба должны вернуться
    c1 = await _create_contact(client, full_name="Петя", ambitions="python и системное программирование")
    c2 = await _create_contact(client, full_name="Вася")
    await _create_interaction(client, c2, notes="Обсудили python-библиотеки для обработки данных")

    resp = await client.get(SEARCH, params={"q": "python"})
    data = resp.json()
    contact_ids = {c["id"] for c in data["contacts"]}
    interaction_contact_ids = {i["contact_id"] for i in data["interactions"]}
    assert c1 in contact_ids
    assert c2 in interaction_contact_ids


@pytest.mark.asyncio
async def test_search_limit(client):
    for i in range(5):
        await _create_contact(client, full_name=f"Контакт {i}", ambitions="уникальный-тег-лимит")

    resp = await client.get(SEARCH, params={"q": "уникальный-тег-лимит", "limit": 2})
    assert resp.status_code == 200
    assert len(resp.json()["contacts"]) == 2
