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


@pytest.mark.asyncio
async def test_list_links_tenant_isolation(client, db_session):
    """GET /contacts/{id}/links для контакта чужого тенанта → 404; чужие связи не утекают."""
    from api.data_base.models import ContactCard, ContactLink, Tenant
    from uuid import uuid4

    other_tenant = Tenant(id=uuid4(), name=f"other-{uuid4().hex[:8]}")
    db_session.add(other_tenant)
    await db_session.flush()

    x1 = ContactCard(id=uuid4(), full_name="X1", tenant_id=other_tenant.id)
    x2 = ContactCard(id=uuid4(), full_name="X2", tenant_id=other_tenant.id)
    db_session.add_all([x1, x2])
    await db_session.flush()
    db_session.add(ContactLink(
        id=uuid4(),
        tenant_id=other_tenant.id,
        contact_id_a=x1.id,
        contact_id_b=x2.id,
        relationship_type="friend",
    ))
    await db_session.commit()

    # Запрос к чужому контакту → 404, а не список его связей.
    resp = await client.get(f"{CONTACTS}/{x1.id}/links")
    assert resp.status_code == 404
