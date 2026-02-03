# Rockfile

**Картотека контактов в стиле Рокфеллера** — приложение для управления персональной картотекой с детальной информацией о каждом человеке. Идея основана на методологии Джона Рокфеллера, у которого было порядка 200 000 карточек с заметками о контактах, встречах, обещаниях и связях между людьми.

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
