"""Полнотекстовый поиск по карточкам и взаимодействиям.

Использует generated-столбцы `search_tsv` (tsvector) + GIN-индексы,
созданные утилитой utils.search_bootstrap.
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


HEADLINE_OPTS = (
    "StartSel=<mark>, StopSel=</mark>, "
    "MaxFragments=1, MaxWords=18, MinWords=5, ShortWord=2"
)


async def search_contacts_and_interactions(
    session: AsyncSession,
    tenant_id,
    query: str,
    limit: int,
) -> tuple[list[dict], list[dict]]:
    """Возвращает два списка: совпадения по контактам и по взаимодействиям.

    Пустой или пробельный `query` возвращает пустые списки (endpoint не должен дёргать БД).
    """
    q = (query or "").strip()
    if not q:
        return [], []

    tenant_where = "AND c.tenant_id = :tenant_id" if tenant_id is not None else ""
    params = {"q": q, "limit": limit, "hopts": HEADLINE_OPTS}
    if tenant_id is not None:
        params["tenant_id"] = str(tenant_id)

    contacts_sql = text(
        f"""
        SELECT
            c.id,
            c.full_name,
            c.email,
            c.phone,
            c.relationship_type,
            ts_rank_cd(c.search_tsv, q.query) AS rank,
            ts_headline(
                'russian',
                concat_ws(' ',
                    c.full_name, c.address, c.ambitions,
                    c.hobbies::jsonb::text, c.interests::jsonb::text, c.goals::jsonb::text
                ),
                q.query,
                :hopts
            ) AS snippet
        FROM contact_cards c
        CROSS JOIN (SELECT websearch_to_tsquery('russian', :q) AS query) q
        WHERE c.search_tsv @@ q.query
          {tenant_where}
        ORDER BY rank DESC, c.full_name ASC
        LIMIT :limit
        """
    )

    interactions_sql = text(
        f"""
        SELECT
            i.id,
            i.contact_id,
            c.full_name AS contact_full_name,
            i.occurred_at,
            i.channel,
            ts_rank_cd(i.search_tsv, q.query) AS rank,
            ts_headline(
                'russian',
                concat_ws(' ', i.notes, i.promises::jsonb::text, i.mentions::jsonb::text),
                q.query,
                :hopts
            ) AS snippet
        FROM contact_interactions i
        JOIN contact_cards c ON c.id = i.contact_id
        CROSS JOIN (SELECT websearch_to_tsquery('russian', :q) AS query) q
        WHERE i.search_tsv @@ q.query
          {tenant_where}
        ORDER BY rank DESC, i.occurred_at DESC
        LIMIT :limit
        """
    )

    contacts_rows = (await session.execute(contacts_sql, params)).mappings().all()
    interactions_rows = (await session.execute(interactions_sql, params)).mappings().all()

    return [dict(r) for r in contacts_rows], [dict(r) for r in interactions_rows]
