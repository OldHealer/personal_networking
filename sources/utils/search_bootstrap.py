"""Идемпотентное добавление tsvector-колонок и GIN-индексов для полнотекстового поиска.

Alembic в проекте не настроен, таблицы создаются через `Base.metadata.create_all`.
Поэтому sdhemy-неизвестные расширения схемы (сгенерированные столбцы, GIN-индексы)
применяем отдельным бутстрапом на старте приложения и в фикстурах тестов.

Используем генерируемые столбцы `STORED` — Postgres пересчитывает tsvector сам при UPDATE/INSERT.
`to_tsvector('russian', ...)` с регконфигом-литералом считается IMMUTABLE, что требуется
для GENERATED ALWAYS AS ... STORED.
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine



# Python json.dumps по умолчанию использует ensure_ascii=True → в колонке JSON кириллица
# сохраняется как \uXXXX. Приведение json::jsonb::text нормализует обратно в UTF-8,
# иначе tsvector токенизирует мусорные "u0444"-токены.

CONTACT_CARDS_SEARCH_DDL = """
ALTER TABLE contact_cards
    ADD COLUMN IF NOT EXISTS search_tsv tsvector
    GENERATED ALWAYS AS (
        to_tsvector(
            'russian',
            coalesce(full_name, '') || ' ' ||
            coalesce(address, '') || ' ' ||
            coalesce(ambitions, '') || ' ' ||
            coalesce(phone, '') || ' ' ||
            coalesce(email, '') || ' ' ||
            coalesce(hobbies::jsonb::text, '') || ' ' ||
            coalesce(interests::jsonb::text, '') || ' ' ||
            coalesce(goals::jsonb::text, '')
        )
    ) STORED
"""

CONTACT_INTERACTIONS_SEARCH_DDL = """
ALTER TABLE contact_interactions
    ADD COLUMN IF NOT EXISTS search_tsv tsvector
    GENERATED ALWAYS AS (
        to_tsvector(
            'russian',
            coalesce(notes, '') || ' ' ||
            coalesce(promises::jsonb::text, '') || ' ' ||
            coalesce(mentions::jsonb::text, '')
        )
    ) STORED
"""

CONTACT_CARDS_SEARCH_INDEX_DDL = (
    "CREATE INDEX IF NOT EXISTS ix_contact_cards_search_tsv "
    "ON contact_cards USING GIN(search_tsv)"
)

CONTACT_INTERACTIONS_SEARCH_INDEX_DDL = (
    "CREATE INDEX IF NOT EXISTS ix_contact_interactions_search_tsv "
    "ON contact_interactions USING GIN(search_tsv)"
)


async def ensure_fulltext_search(engine: AsyncEngine) -> None:
    """Добавляет генерируемые tsvector-колонки и GIN-индексы. Идемпотентно."""
    async with engine.begin() as conn:
        await conn.execute(text(CONTACT_CARDS_SEARCH_DDL))
        await conn.execute(text(CONTACT_INTERACTIONS_SEARCH_DDL))
        await conn.execute(text(CONTACT_CARDS_SEARCH_INDEX_DDL))
        await conn.execute(text(CONTACT_INTERACTIONS_SEARCH_INDEX_DDL))
