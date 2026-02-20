# Rockfile

**Картотека контактов Рокфеллера** — приложение для управления персональной картотекой с детальной информацией о каждом человеке. Идея основана на методологии Джона Рокфеллера, у которого было порядка 200 000 карточек с заметками о контактах, встречах, обещаниях и связях между людьми.

## Возможности

- **Карточки контактов** — имя, контакты, дата знакомства, интересы, семья, заметки, обещания, цели
- **Связи между контактами** — граф отношений (кто кого знает, семья, друзья, коллеги)
- **История взаимодействий** — встречи, звонки, переписки с заметками и обещаниями
- **Персонализация** — максимум контекста для тёплого, осмысленного общения

## Технологии

- **Backend:** FastAPI
- **БД:** PostgreSQL (async через SQLAlchemy 2.0)
- **Миграции:** Alembic
- **Конфигурация:** pydantic-settings

## Требования

- Python ≥ 3.12
- PostgreSQL
- [Poetry](https://python-poetry.org/)

## Установка

```bash
# Клонировать репозиторий
git clone <repo-url>
cd personal_networking

# Установить зависимости
poetry install

# Активировать окружение
poetry shell
```

## Конфигурация

Создайте файл `.env` в корне проекта (или `.env.local` для локальной разработки):

```env
# База данных (обязательно)
DATABASE__DB_USER=postgres
DATABASE__DB_PASSWORD=your_password
DATABASE__DB_HOST=localhost
DATABASE__DB_PORT=5432
DATABASE__DB_NAME=rockfile

# API (опционально)
API__HOST=0.0.0.0
API__PORT=8000

# Keycloak admin API (нужно для /api/v1/auth/register)
KEYCLOAK_ADMIN__BASE_URL=http://localhost:8181
KEYCLOAK_ADMIN__REALM=rockfile
KEYCLOAK_ADMIN__CLIENT_ID=rockfile-admin-cli
KEYCLOAK_ADMIN__CLIENT_SECRET=your_secret
```

## Запуск

```bash
# Из корня проекта
cd sources
python main.py
```

Или через uvicorn:

```bash
cd sources
uvicorn api.fastapi_app:app --host 0.0.0.0 --port 8000 --reload
```

Сервер будет доступен по адресу: `http://localhost:8000`

## API

- **Swagger UI:** http://localhost:8000/api/docs
- **ReDoc:** http://localhost:8000/api/redoc
- **OpenAPI JSON:** http://localhost:8000/api/openapi.json

### Базовые эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/` | Корневой эндпоинт |
| GET | `/api/v1/ping` | Проверка доступности |

## Проверка токена (Keycloak)

### 1) Получить access token (через парольный grant)
> В Keycloak у клиента `rockfile-api` должен быть включен `Direct access grants`.

**Linux/WSL:**
```bash
curl -X POST "http://localhost:8181/realms/rockfile/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=rockfile-api" \
  -d "client_secret=YOUR_SECRET" \
  -d "username=YOUR_USER" \
  -d "password=YOUR_PASS"
```

**PowerShell:**
```powershell
curl -X POST "http://localhost:8181/realms/rockfile/protocol/openid-connect/token" `
  -H "Content-Type: application/x-www-form-urlencoded" `
  -d "grant_type=password" `
  -d "client_id=rockfile-api" `
  -d "client_secret=YOUR_SECRET" `
  -d "username=YOUR_USER" `
  -d "password=YOUR_PASS"
```

### 2) Проверить токен через скрипт
```bash
poetry run python sources/utils/token_inspect.py <ACCESS_TOKEN>
```

В ответе ищите:
- `realm_access.roles` (например, `superadmin`)
- `iss` (должен совпадать с `http://localhost:8181/realms/rockfile`)

## Структура проекта

```
personal_networking/
├── docs/
│   ├── ARCHITECTURE.md      # Архитектурное видение, сущности, технологии
│   └── DEVELOPMENT_PLAN.md  # План разработки по фазам
├── sources/
│   ├── api/
│   │   ├── data_base/       # Модели, БД, DAO
│   │   └── fastapi_app.py   # Приложение FastAPI
│   ├── main.py              # Точка входа
│   ├── settings.py          # Конфигурация
│   └── utils/               # Утилиты (логирование и др.)
├── pyproject.toml
└── README.md
```

## Документация

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — архитектура, доменная модель, сущности (ContactCard, ContactLink, ContactInteraction), API, перспективы (ИИ-агент, мобильное приложение)
- [DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md) — план разработки по фазам (MVP API → связи → поиск → авторизация → расширения)

## Статус разработки

Проект на этапе MVP: настроен FastAPI, модели данных, базовая структура. Полноценный CRUD API и миграции — в разработке по плану.

## Лицензия

Private project.
