"""Интеграционные тесты для /api/v1/contacts/{id}/links."""
import pytest

CONTACTS = "/api/v1/contacts"


async def _make_contact(client, name: str) -> str:
    resp = await client.post(CONTACTS, json={"full_name": name})
    assert resp.status_code == 200
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_list_empty(client):
    cid = await _make_contact(client, "Один")
    resp = await client.get(f"{CONTACTS}/{cid}/links")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_link(client):
    a = await _make_contact(client, "Алексей")
    b = await _make_contact(client, "Борис")

    resp = await client.post(
        f"{CONTACTS}/{a}/links",
        json={"contact_id_b": b, "relationship_type": "colleague", "context": "тот же отдел", "is_directed": False},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["contact_id_a"] == a
    assert body["contact_id_b"] == b
    assert body["relationship_type"] == "colleague"
    assert body["is_directed"] is False


@pytest.mark.asyncio
async def test_create_link_contact_not_found(client):
    a = await _make_contact(client, "Один")
    resp = await client.post(
        f"{CONTACTS}/{a}/links",
        json={"contact_id_b": "00000000-0000-0000-0000-000000000000", "relationship_type": "friend"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_link_from_either_side(client):
    """Связь должна светиться как у инициатора, так и у второго контакта."""
    a = await _make_contact(client, "Алексей")
    b = await _make_contact(client, "Борис")
    await client.post(
        f"{CONTACTS}/{a}/links",
        json={"contact_id_b": b, "relationship_type": "friend"},
    )

    resp_a = await client.get(f"{CONTACTS}/{a}/links")
    resp_b = await client.get(f"{CONTACTS}/{b}/links")
    assert len(resp_a.json()) == 1
    assert len(resp_b.json()) == 1


@pytest.mark.asyncio
async def test_update_link(client):
    a = await _make_contact(client, "А")
    b = await _make_contact(client, "Б")
    create = await client.post(
        f"{CONTACTS}/{a}/links",
        json={"contact_id_b": b, "relationship_type": "colleague"},
    )
    link_id = create.json()["id"]

    resp = await client.patch(
        f"{CONTACTS}/{a}/links/{link_id}",
        json={"relationship_type": "friend", "is_directed": True, "context": "школа"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["relationship_type"] == "friend"
    assert body["is_directed"] is True
    assert body["context"] == "школа"


@pytest.mark.asyncio
async def test_delete_link(client):
    a = await _make_contact(client, "А")
    b = await _make_contact(client, "Б")
    create = await client.post(
        f"{CONTACTS}/{a}/links",
        json={"contact_id_b": b, "relationship_type": "colleague"},
    )
    link_id = create.json()["id"]

    resp = await client.delete(f"{CONTACTS}/{a}/links/{link_id}")
    assert resp.status_code == 204

    resp = await client.get(f"{CONTACTS}/{a}/links")
    assert resp.json() == []


@pytest.mark.asyncio
async def test_update_link_not_found(client):
    a = await _make_contact(client, "А")
    resp = await client.patch(
        f"{CONTACTS}/{a}/links/00000000-0000-0000-0000-000000000000",
        json={"relationship_type": "friend"},
    )
    assert resp.status_code == 404
