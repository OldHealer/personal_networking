"""Интеграционные тесты GET /api/v1/promises."""
from datetime import datetime, timezone


async def _create_contact(client, name="Test"):
    r = await client.post("/api/v1/contacts", json={"full_name": name})
    assert r.status_code in (200, 201)
    return r.json()["id"]


async def _add_interaction_with_promises(client, contact_id, promises: list[dict]):
    r = await client.post(
        f"/api/v1/contacts/{contact_id}/interactions",
        json={
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "channel": "встреча",
            "notes": "тест",
            "promises": promises,
        },
    )
    assert r.status_code in (200, 201)
    return r.json()["id"]


async def test_promises_empty(client):
    r = await client.get("/api/v1/promises")
    assert r.status_code == 200
    assert r.json() == {"items": [], "total": 0}


async def test_promises_returns_open(client):
    cid = await _create_contact(client, "Алексей")
    await _add_interaction_with_promises(client, cid, [
        {"text": "позвонить на неделе", "direction": "mine"},
        {"text": "прислать презентацию", "direction": "theirs"},
    ])

    r = await client.get("/api/v1/promises")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    texts = {item["text"] for item in body["items"]}
    assert texts == {"позвонить на неделе", "прислать презентацию"}
    assert all(item["contact_name"] == "Алексей" for item in body["items"])
    assert all(item["completed_at"] is None for item in body["items"])


async def test_promises_filter_direction_mine(client):
    cid = await _create_contact(client, "Борис")
    await _add_interaction_with_promises(client, cid, [
        {"text": "я обещал", "direction": "mine"},
        {"text": "он обещал", "direction": "theirs"},
    ])

    r = await client.get("/api/v1/promises?direction=mine")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["text"] == "я обещал"
    assert items[0]["direction"] == "mine"


async def test_promises_filter_direction_theirs(client):
    cid = await _create_contact(client, "Виктор")
    await _add_interaction_with_promises(client, cid, [
        {"text": "мои обязательства", "direction": "mine"},
        {"text": "его обязательства", "direction": "theirs"},
    ])

    r = await client.get("/api/v1/promises?direction=theirs")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["direction"] == "theirs"


async def test_promises_open_false_returns_all(client):
    cid = await _create_contact(client, "Геннадий")
    inter_id = await _add_interaction_with_promises(client, cid, [
        {"text": "открытое обещание", "direction": "mine"},
    ])

    # Закрываем обещание
    promises_r = await client.get("/api/v1/promises")
    promise_id = promises_r.json()["items"][0]["promise_id"]
    await client.post(f"/api/v1/contacts/{cid}/promises/{promise_id}/complete")

    # open=true — не должно быть
    r_open = await client.get("/api/v1/promises?open=true")
    assert r_open.json()["total"] == 0

    # open=false — должно быть
    r_all = await client.get("/api/v1/promises?open=false")
    assert r_all.json()["total"] == 1
    assert r_all.json()["items"][0]["completed_at"] is not None


async def test_promises_across_multiple_contacts(client):
    cid1 = await _create_contact(client, "Дима")
    cid2 = await _create_contact(client, "Елена")
    await _add_interaction_with_promises(client, cid1, [{"text": "от Димы", "direction": "mine"}])
    await _add_interaction_with_promises(client, cid2, [{"text": "от Елены", "direction": "theirs"}])

    r = await client.get("/api/v1/promises")
    assert r.status_code == 200
    names = {item["contact_name"] for item in r.json()["items"]}
    assert names == {"Дима", "Елена"}


async def test_promises_tenant_isolation(client, db_session):
    from uuid import uuid4
    from api.data_base.models import AppUser, Tenant
    from api.auth.deps import CurrentUser
    from api.auth.keycloak_module import TokenPayload
    from httpx import ASGITransport, AsyncClient

    # Создаём второго пользователя с другим tenant
    tenant2 = Tenant(id=uuid4(), name=f"other-{uuid4().hex[:8]}")
    db_session.add(tenant2)
    await db_session.flush()
    user2 = AppUser(
        id=uuid4(),
        keycloak_sub=f"other-sub-{uuid4().hex}",
        username="other",
        email=f"other-{uuid4().hex[:8]}@example.com",
        tenant_id=tenant2.id,
    )
    db_session.add(user2)
    await db_session.commit()

    # Первый юзер добавляет контакт с обещанием
    cid = await _create_contact(client, "Чужой контакт")
    await _add_interaction_with_promises(client, cid, [{"text": "чужое обещание", "direction": "mine"}])

    # Второй юзер не должен видеть обещания первого
    from api.data_base.base import db, get_db_session
    from api.auth.deps import get_current_user
    from api.fastapi_app import http_exception_handler, validation_exception_handler, generic_exception_handler
    from fastapi import FastAPI, HTTPException
    from fastapi.exceptions import RequestValidationError
    from api.routers.v1.promises import promises_router as pr

    app2 = FastAPI()
    app2.include_router(pr)
    app2.add_exception_handler(HTTPException, http_exception_handler)
    app2.add_exception_handler(RequestValidationError, validation_exception_handler)
    app2.add_exception_handler(Exception, generic_exception_handler)

    token2 = TokenPayload(sub=user2.keycloak_sub, preferred_username=user2.username, email=user2.email)
    cu2 = CurrentUser(token=token2, db_user=user2)

    async def _override_user2():
        return cu2

    async def _override_session2():
        async with db.session_factory() as s:
            yield s

    app2.dependency_overrides[get_current_user] = _override_user2
    app2.dependency_overrides[get_db_session] = _override_session2

    async with AsyncClient(transport=ASGITransport(app=app2), base_url="http://test") as ac2:
        r = await ac2.get("/api/v1/promises")
    assert r.status_code == 200
    assert r.json()["total"] == 0
