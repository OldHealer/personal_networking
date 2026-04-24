"""Интеграционные тесты для /api/v1/contacts."""
import pytest


BASE = "/api/v1/contacts"


@pytest.mark.asyncio
async def test_list_empty(client):
    resp = await client.get(BASE)
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["page"] == 1


@pytest.mark.asyncio
async def test_create_and_get(client):
    payload = {"full_name": "Иван Петров", "email": "ivan@example.com", "phone": "+79991112233"}
    resp = await client.post(BASE, json=payload)
    assert resp.status_code == 200
    created = resp.json()
    assert created["full_name"] == "Иван Петров"
    assert created["email"] == "ivan@example.com"
    cid = created["id"]

    resp = await client.get(f"{BASE}/{cid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == cid


@pytest.mark.asyncio
async def test_create_validation_error(client):
    # full_name обязателен
    resp = await client.post(BASE, json={"email": "x@example.com"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_not_found(client):
    resp = await client.get(f"{BASE}/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update(client):
    resp = await client.post(BASE, json={"full_name": "Мария"})
    cid = resp.json()["id"]

    resp = await client.patch(f"{BASE}/{cid}", json={"phone": "+71234567890"})
    assert resp.status_code == 200
    assert resp.json()["phone"] == "+71234567890"
    assert resp.json()["full_name"] == "Мария"


@pytest.mark.asyncio
async def test_delete(client):
    resp = await client.post(BASE, json={"full_name": "Удаляемый"})
    cid = resp.json()["id"]

    resp = await client.delete(f"{BASE}/{cid}")
    assert resp.status_code == 204

    resp = await client.get(f"{BASE}/{cid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_pagination_and_sort(client):
    for name in ["Анна", "Борис", "Виктор"]:
        await client.post(BASE, json={"full_name": name})

    resp = await client.get(BASE, params={"sort": "name", "per_page": 2, "page": 1})
    body = resp.json()
    assert body["total"] == 3
    assert [i["full_name"] for i in body["items"]] == ["Анна", "Борис"]

    resp = await client.get(BASE, params={"sort": "name", "per_page": 2, "page": 2})
    assert [i["full_name"] for i in resp.json()["items"]] == ["Виктор"]


@pytest.mark.asyncio
async def test_search_by_name(client):
    for payload in [
        {"full_name": "Пётр Иванов", "email": "petr@example.com"},
        {"full_name": "Анна Смирнова", "email": "anna@example.com"},
        {"full_name": "Иван Сидоров", "email": "sid@example.com"},
    ]:
        await client.post(BASE, json=payload)

    resp = await client.get(BASE, params={"q": "иванов"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["full_name"] == "Пётр Иванов"


@pytest.mark.asyncio
async def test_search_by_email(client):
    await client.post(BASE, json={"full_name": "Первый", "email": "alice@example.com"})
    await client.post(BASE, json={"full_name": "Второй", "email": "bob@foo.com"})

    resp = await client.get(BASE, params={"q": "example.com"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "alice@example.com"


@pytest.mark.asyncio
async def test_search_empty_query_returns_all(client):
    await client.post(BASE, json={"full_name": "Одиночка"})
    # q="" и q="   " не должны фильтровать
    for q in ["", "   "]:
        resp = await client.get(BASE, params={"q": q})
        assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_search_case_insensitive(client):
    await client.post(BASE, json={"full_name": "Катерина"})
    resp = await client.get(BASE, params={"q": "КАТЕРИНА"})
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_last_contact_before_includes_contacts_without_interactions(client, db_session, test_user):
    """Контакт без взаимодействий, созданный давно, должен попасть в фильтр."""
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4
    from api.data_base.models import ContactCard

    # Свежий контакт через API — создан сейчас, не должен попадать в "давно не общались".
    await client.post(BASE, json={"full_name": "Свежий"})

    # Старый контакт — вставляем напрямую в БД с антидатированным created_at.
    old = ContactCard(
        id=uuid4(),
        full_name="Старый",
        tenant_id=test_user.db_user.tenant_id,
        created_at=datetime.now(timezone.utc) - timedelta(days=60),
    )
    db_session.add(old)
    await db_session.commit()

    resp = await client.get(BASE, params={"last_contact_before": 30})
    names = [i["full_name"] for i in resp.json()["items"]]
    assert "Старый" in names
    assert "Свежий" not in names


@pytest.mark.asyncio
async def test_last_contact_before_with_recent_interaction(client):
    """Если есть свежее взаимодействие, контакт не попадает в "давно не общались"."""
    from datetime import datetime, timezone

    create = await client.post(BASE, json={"full_name": "Активный"})
    cid = create.json()["id"]
    await client.post(
        f"{BASE}/{cid}/interactions",
        json={"occurred_at": datetime.now(timezone.utc).isoformat()},
    )

    resp = await client.get(BASE, params={"last_contact_before": 7})
    names = [i["full_name"] for i in resp.json()["items"]]
    assert "Активный" not in names


@pytest.mark.asyncio
async def test_last_contact_before_with_old_interaction(client, db_session):
    """Старое взаимодействие → контакт в "давно не общались"."""
    from datetime import datetime, timedelta, timezone

    create = await client.post(BASE, json={"full_name": "Давно_не_виделись"})
    cid = create.json()["id"]
    old_date = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
    await client.post(f"{BASE}/{cid}/interactions", json={"occurred_at": old_date})

    resp = await client.get(BASE, params={"last_contact_before": 30})
    names = [i["full_name"] for i in resp.json()["items"]]
    assert "Давно_не_виделись" in names


@pytest.mark.asyncio
async def test_last_contact_before_validation(client):
    # N должен быть >= 1
    resp = await client.get(BASE, params={"last_contact_before": 0})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_filter_by_relationship_type(client):
    await client.post(BASE, json={"full_name": "Коллега", "relationship_type": "colleague"})
    await client.post(BASE, json={"full_name": "Друг", "relationship_type": "friend"})
    await client.post(BASE, json={"full_name": "Без типа"})

    resp = await client.get(BASE, params={"relationship_type": "colleague"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["full_name"] == "Коллега"


@pytest.mark.asyncio
async def test_sort_by_last_contact_at(client):
    """Сортировка: самые свежие встречи сверху, без встреч — в конец."""
    from datetime import datetime, timedelta, timezone

    a = (await client.post(BASE, json={"full_name": "А_свежий"})).json()["id"]
    b = (await client.post(BASE, json={"full_name": "Б_давний"})).json()["id"]
    await client.post(BASE, json={"full_name": "В_без_встреч"})

    now = datetime.now(timezone.utc)
    await client.post(f"{BASE}/{a}/interactions", json={"occurred_at": now.isoformat()})
    await client.post(f"{BASE}/{b}/interactions",
                      json={"occurred_at": (now - timedelta(days=10)).isoformat()})

    resp = await client.get(BASE, params={"sort": "last_contact_at"})
    names = [i["full_name"] for i in resp.json()["items"]]
    assert names == ["А_свежий", "Б_давний", "В_без_встреч"]


@pytest.mark.asyncio
async def test_has_birthday_soon(client):
    """Контакты с ДР в пределах N дней должны попадать в результат."""
    from datetime import date, timedelta

    today = date.today()
    in_5_days = today + timedelta(days=5)
    in_60_days = today + timedelta(days=60)

    await client.post(BASE, json={"full_name": "Близко", "birthday": in_5_days.isoformat()})
    await client.post(BASE, json={"full_name": "Далеко", "birthday": in_60_days.isoformat()})
    await client.post(BASE, json={"full_name": "Без_ДР"})

    resp = await client.get(BASE, params={"has_birthday_soon": 14})
    names = [i["full_name"] for i in resp.json()["items"]]
    assert "Близко" in names
    assert "Далеко" not in names
    assert "Без_ДР" not in names


@pytest.mark.asyncio
async def test_has_birthday_soon_year_wraparound(client):
    """ДР через 3 дня от сегодня работает, даже если год ДР — прошлый."""
    from datetime import date, timedelta

    near = date.today() + timedelta(days=3)
    near_old_year = date(1990, near.month, near.day)

    await client.post(BASE, json={"full_name": "Близко", "birthday": near_old_year.isoformat()})

    resp = await client.get(BASE, params={"has_birthday_soon": 7})
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_tenant_isolation(client, db_session):
    """Контакт из чужого тенанта не должен возвращаться в списке."""
    from api.data_base.models import ContactCard, Tenant
    from uuid import uuid4

    other_tenant = Tenant(id=uuid4(), name=f"other-{uuid4().hex[:8]}")
    db_session.add(other_tenant)
    await db_session.flush()
    stranger = ContactCard(id=uuid4(), full_name="Чужой", tenant_id=other_tenant.id)
    db_session.add(stranger)
    await db_session.commit()

    await client.post(BASE, json={"full_name": "Свой"})

    resp = await client.get(BASE)
    body = resp.json()
    names = [i["full_name"] for i in body["items"]]
    assert "Свой" in names
    assert "Чужой" not in names
    assert body["total"] == 1


@pytest.mark.asyncio
async def test_stats_empty(client):
    resp = await client.get(f"{BASE}/stats")
    assert resp.status_code == 200
    assert resp.json() == {"total": 0, "by_type": {}}


@pytest.mark.asyncio
async def test_stats_groups_by_relationship_type(client):
    await client.post(BASE, json={"full_name": "Ann", "relationship_type": "friend"})
    await client.post(BASE, json={"full_name": "Bob", "relationship_type": "friend"})
    await client.post(BASE, json={"full_name": "Cid", "relationship_type": "colleague"})
    # контакт без relationship_type → ключ "other"
    await client.post(BASE, json={"full_name": "Dan"})

    resp = await client.get(f"{BASE}/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 4
    assert body["by_type"] == {"friend": 2, "colleague": 1, "other": 1}


@pytest.mark.asyncio
async def test_stats_tenant_isolation(client, db_session):
    """Статистика не должна учитывать контакты чужого тенанта."""
    from api.data_base.models import ContactCard, Tenant
    from uuid import uuid4

    other_tenant = Tenant(id=uuid4(), name=f"other-{uuid4().hex[:8]}")
    db_session.add(other_tenant)
    await db_session.flush()
    db_session.add_all([
        ContactCard(id=uuid4(), full_name="X1", relationship_type="friend", tenant_id=other_tenant.id),
        ContactCard(id=uuid4(), full_name="X2", relationship_type="friend", tenant_id=other_tenant.id),
    ])
    await db_session.commit()

    await client.post(BASE, json={"full_name": "Свой", "relationship_type": "colleague"})

    resp = await client.get(f"{BASE}/stats")
    body = resp.json()
    assert body["total"] == 1
    assert body["by_type"] == {"colleague": 1}
