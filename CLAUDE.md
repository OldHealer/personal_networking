# Rockfile — Personal Networking CRM

## Стек
- **Backend:** FastAPI + SQLAlchemy async + PostgreSQL + Alembic
- **Auth:** Keycloak (порт 8282), JWT Bearer токены в localStorage
- **AI:** LangGraph агент + FastMCP + Ollama (qwen2.5:14b)
- **Frontend:** Vanilla JS (ES modules), без фреймворков, без сборщиков

## Запуск
```bash
docker compose up -d
```

## Структура
```
sources/
  api/
    routers/v1/   — FastAPI роутеры (contacts, interactions, links, agents, auth)
    services/     — бизнес-логика (принимают session как аргумент)
    schemas/      — Pydantic модели
    data_base/    — SQLAlchemy модели и сессия
  agents/
    prepare_meeting_agent.py  — LangGraph агент подготовки к встрече
    mcp_server.py             — FastMCP сервер
    tools/                    — инструменты агента
  web/
    assets/css/styles.css     — весь CSS (тёмная тема через [data-theme="dark"])
    assets/js/ui.js            — общие утилиты (тема, тост, footer)
    assets/js/contact.js       — страница контакта
    assets/js/contacts.js      — список контактов
    assets/js/auth.js          — вход/регистрация
  settings.py   — конфиг через Pydantic Settings (не os.getenv напрямую)
```

## Соглашения
- Python: snake_case, async везде, сервисы всегда принимают `session` первым аргументом
- Новые API эндпоинты — всегда проверять `tenant_id` из `current_user.db_user.tenant_id`
- JS: ES modules, camelCase, импорты общих утилит из `./ui.js`
- CSS: BEM-подобные классы, тёмная тема через `[data-theme="dark"]` селекторы в конце файла
- Антиблокировка рендера: inline `<script>` в `<head>` для применения темы до CSS

## Перед коммитом
- Обновить `CHANGELOG.md` (секция `## [Unreleased]`)
- Убедиться что `.env` не попал в staging
