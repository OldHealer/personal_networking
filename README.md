# Rockfile

> **A personal contact and card-making system inspired by the Rockefeller card index, powered by AI.**

![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.128-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063?style=for-the-badge&logo=pydantic&logoColor=white)
![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)  
![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Keycloak OIDC](https://img.shields.io/badge/Keycloak-OIDC-5B68A3?style=for-the-badge&logo=keycloak&logoColor=white)
![Poetry](https://img.shields.io/badge/Poetry-deps-60A5FA?style=for-the-badge&logo=poetry&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-agents-8e4c34?style=for-the-badge&labelColor=f7f2eb)
![Ollama](https://img.shields.io/badge/Ollama-local%20LLM-000000?style=for-the-badge&logo=ollama&logoColor=white)  
![Stack](https://img.shields.io/badge/stack-FastAPI%20%7C%20PostgreSQL%20%7C%20Keycloak-8e4c34?style=for-the-badge&labelColor=f7f2eb)
![Frontend](https://img.shields.io/badge/frontend-HTML%20%2B%20CSS%20%2B%20JS-e3b089?style=for-the-badge&labelColor=2b2a27)
![Status](https://img.shields.io/badge/status-MVP_in_progress-e3b089?style=for-the-badge&labelColor=2b2a27)

---

**Rockfile** (Rockefeller-style contact file) helps maintain a personal network: detailed **contact cards**, **who-knows-whom** links, and a timeline of **interactions** (meetings, calls, notes, promises). The goal is rich context for warm, meaningful follow-ups.

## Features

- **Contact cards** — identity (name, phone, email, address), relationship type, personal block (family, birthday, notes, interests), goals & ambitions, aggregated **promises**
- **Relationships graph** — `ContactLink` between people in your file (friend, colleague, family, etc.)
- **Interaction history** — `ContactInteraction` with channel, notes, promises; list views show **last interaction** where relevant
- **AI meeting prep** — optional LangGraph flow + `POST /api/v1/agents/prepare-meeting` (local Ollama or MCP mode; see `docs/AGENTS.md`)
- **Web UI** — static HTML/CSS/JS: home, login (Keycloak), contacts list, contact detail (sections + links + interactions)
- **API docs** — Swagger at `/api/docs`

## Tech stack

| Layer | Choice |
|--------|--------|
| Backend | FastAPI, Pydantic v2, pydantic-settings |
| DB | PostgreSQL, SQLAlchemy 2.0 async, asyncpg |
| Auth | Keycloak (JWT / OIDC), multi-tenant `tenant_id` on data |
| Migrations | Alembic when `alembic.ini` is present; otherwise tables are created on startup |
| Agents | LangGraph, langchain-ollama, FastMCP (tools/MCP server) |
| Frontend | Classic HTML/CSS/JS under `sources/web/`, served by FastAPI |

## Quick start

### With Docker Compose

From the repository root:

```bash
docker compose up --build
```

Typical ports:

| Service | URL / port |
|---------|------------|
| API + web | http://localhost:8000 |
| API docs | http://localhost:8000/api/docs |
| PostgreSQL | `localhost:5532` → container `5432` |
| Keycloak | http://localhost:8181 |

Environment variables follow `sources/settings.py` (prefixes like `DATABASE__…`, `KEYCLOAK__…`). The compose file sets defaults for local dev.

### Local Python (Poetry)

Requires **Python 3.12+**, PostgreSQL, and Keycloak configured like in compose.

```bash
poetry install
poetry run python sources/main.py
```

`PYTHONPATH` should include `sources` (the Docker image sets `PYTHONPATH=/app/sources`).

### AI / Ollama (optional)

For the meeting-prep agent, run [Ollama](https://ollama.com) on the host (e.g. `http://localhost:11434`). In Docker, `OLLAMA_BASE_URL=http://host.docker.internal:11434` is used so the API container can reach the host.

## Project layout (short)

- `sources/api/` — FastAPI app, routers (`contacts`, `links`, `interactions`, `auth`, `agents`), schemas, services
- `sources/web/` — frontend pages and `assets/`
- `sources/agents/` — LangGraph / MCP-related agent code
- `docs/` — architecture, development plan, AI agents notes (`docs/AGENTS.md`)

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — domain model, layers, product directions
- [`docs/DEVELOPMENT_PLAN.md`](docs/DEVELOPMENT_PLAN.md) — phased checklist with progress column
- [`docs/AGENTS.md`](docs/AGENTS.md) — AI agents, MCP vs local mode, meeting prep

Developer-facing docs are partly in Russian; this README stays in English for a neutral onboarding surface.

## Development status

- Architecture, core models, REST API for contacts / links / interactions
- Web UI for list + detail, Keycloak login flow
- Meeting prep agent endpoint and tooling (evolving)
- Further items: search, filters, Telegram/Mobile as in `DEVELOPMENT_PLAN.md`

## License / usage

Private project.  
Ideas or questions: [Telegram](https://t.me/old_healer).
