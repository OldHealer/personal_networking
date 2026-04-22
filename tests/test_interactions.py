"""Интеграционные тесты для /api/v1/contacts/{id}/interactions и promises."""
from datetime import datetime, timedelta, timezone

import pytest

CONTACTS = "/api/v1/contacts"


async def _make_contact(client, name: str = "Тест") -> str:
    resp = await client.post(CONTACTS, json={"full_name": name})
    return resp.json()["id"]


def _iso(dt: datetime) -> str:
    return dt.isoformat()


@pytest.mark.asyncio
async def test_create_and_list_interactions(client):
    cid = await _make_contact(client)
    now = datetime.now(timezone.utc)

    for offset_days, note in [(2, "второе"), (0, "сегодня"), (5, "раньше")]:
        await client.post(
            f"{CONTACTS}/{cid}/interactions",
            json={
                "occurred_at": _iso(now - timedelta(days=offset_days)),
                "channel": "meeting",
                "notes": note,
            },
        )

    resp = await client.get(f"{CONTACTS}/{cid}/interactions")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 3
    # Сортировка: от свежего к старому
    assert [i["notes"] for i in items] == ["сегодня", "второе", "раньше"]


@pytest.mark.asyncio
async def test_create_interaction_contact_not_found(client):
    resp = await client.post(
        f"{CONTACTS}/00000000-0000-0000-0000-000000000000/interactions",
        json={"occurred_at": _iso(datetime.now(timezone.utc))},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_interaction(client):
    cid = await _make_contact(client)
    create = await client.post(
        f"{CONTACTS}/{cid}/interactions",
        json={"occurred_at": _iso(datetime.now(timezone.utc)), "notes": "старый текст"},
    )
    iid = create.json()["id"]

    resp = await client.patch(
        f"{CONTACTS}/{cid}/interactions/{iid}",
        json={"notes": "новый текст", "channel": "call"},
    )
    assert resp.status_code == 200
    assert resp.json()["notes"] == "новый текст"
    assert resp.json()["channel"] == "call"


@pytest.mark.asyncio
async def test_delete_interaction(client):
    cid = await _make_contact(client)
    create = await client.post(
        f"{CONTACTS}/{cid}/interactions",
        json={"occurred_at": _iso(datetime.now(timezone.utc))},
    )
    iid = create.json()["id"]

    resp = await client.delete(f"{CONTACTS}/{cid}/interactions/{iid}")
    assert resp.status_code == 204

    resp = await client.get(f"{CONTACTS}/{cid}/interactions")
    assert resp.json() == []


@pytest.mark.asyncio
async def test_promises_aggregated_into_contact(client):
    """После создания взаимодействия с обещаниями они появляются в ContactCard.promises."""
    cid = await _make_contact(client)
    await client.post(
        f"{CONTACTS}/{cid}/interactions",
        json={
            "occurred_at": _iso(datetime.now(timezone.utc)),
            "promises": [
                {"text": "прислать презентацию", "direction": "mine"},
                {"text": "подарить книгу", "direction": "theirs"},
            ],
        },
    )

    resp = await client.get(f"{CONTACTS}/{cid}")
    promises = resp.json()["promises"]
    assert len(promises) == 2
    texts = {p["text"] for p in promises}
    assert texts == {"прислать презентацию", "подарить книгу"}
    # Каждому обещанию присвоен id и interaction_id, completed_at по умолчанию None
    for p in promises:
        assert p["id"]
        assert p["interaction_id"]
        assert p["completed_at"] is None


@pytest.mark.asyncio
async def test_complete_promise(client):
    cid = await _make_contact(client)
    await client.post(
        f"{CONTACTS}/{cid}/interactions",
        json={
            "occurred_at": _iso(datetime.now(timezone.utc)),
            "promises": [{"text": "написать письмо", "direction": "mine"}],
        },
    )
    contact = (await client.get(f"{CONTACTS}/{cid}")).json()
    promise_id = contact["promises"][0]["id"]

    resp = await client.post(f"{CONTACTS}/{cid}/promises/{promise_id}/complete")
    assert resp.status_code == 204

    updated = (await client.get(f"{CONTACTS}/{cid}")).json()
    assert updated["promises"][0]["completed_at"] is not None


@pytest.mark.asyncio
async def test_complete_promise_not_found(client):
    cid = await _make_contact(client)
    resp = await client.post(
        f"{CONTACTS}/{cid}/promises/00000000-0000-0000-0000-000000000000/complete"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_promise_text(client):
    cid = await _make_contact(client)
    await client.post(
        f"{CONTACTS}/{cid}/interactions",
        json={
            "occurred_at": _iso(datetime.now(timezone.utc)),
            "promises": [{"text": "исходный текст", "direction": "mine"}],
        },
    )
    pid = (await client.get(f"{CONTACTS}/{cid}")).json()["promises"][0]["id"]

    resp = await client.patch(f"{CONTACTS}/{cid}/promises/{pid}", json={"text": "новый текст"})
    assert resp.status_code == 204, resp.text

    updated = (await client.get(f"{CONTACTS}/{cid}")).json()["promises"][0]
    assert updated["text"] == "новый текст"
    assert updated["direction"] == "mine"


@pytest.mark.asyncio
async def test_update_promise_direction(client):
    cid = await _make_contact(client)
    await client.post(
        f"{CONTACTS}/{cid}/interactions",
        json={
            "occurred_at": _iso(datetime.now(timezone.utc)),
            "promises": [{"text": "что-то", "direction": "mine"}],
        },
    )
    pid = (await client.get(f"{CONTACTS}/{cid}")).json()["promises"][0]["id"]

    await client.patch(f"{CONTACTS}/{cid}/promises/{pid}", json={"direction": "theirs"})
    updated = (await client.get(f"{CONTACTS}/{cid}")).json()["promises"][0]
    assert updated["direction"] == "theirs"


@pytest.mark.asyncio
async def test_delete_promise(client):
    cid = await _make_contact(client)
    await client.post(
        f"{CONTACTS}/{cid}/interactions",
        json={
            "occurred_at": _iso(datetime.now(timezone.utc)),
            "promises": [
                {"text": "первое", "direction": "mine"},
                {"text": "второе", "direction": "theirs"},
            ],
        },
    )
    before = (await client.get(f"{CONTACTS}/{cid}")).json()["promises"]
    assert len(before) == 2
    target = next(p for p in before if p["text"] == "первое")

    resp = await client.delete(f"{CONTACTS}/{cid}/promises/{target['id']}")
    assert resp.status_code == 204

    after = (await client.get(f"{CONTACTS}/{cid}")).json()["promises"]
    assert len(after) == 1
    assert after[0]["text"] == "второе"


@pytest.mark.asyncio
async def test_delete_promise_not_found(client):
    cid = await _make_contact(client)
    resp = await client.delete(
        f"{CONTACTS}/{cid}/promises/00000000-0000-0000-0000-000000000000"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_interaction_rebuilds_promises(client):
    """При удалении взаимодействия обещания уходят из карточки."""
    cid = await _make_contact(client)
    create = await client.post(
        f"{CONTACTS}/{cid}/interactions",
        json={
            "occurred_at": _iso(datetime.now(timezone.utc)),
            "promises": [{"text": "что-то", "direction": "mine"}],
        },
    )
    iid = create.json()["id"]

    before = (await client.get(f"{CONTACTS}/{cid}")).json()
    assert len(before["promises"]) == 1

    await client.delete(f"{CONTACTS}/{cid}/interactions/{iid}")

    after = (await client.get(f"{CONTACTS}/{cid}")).json()
    assert after["promises"] == []
