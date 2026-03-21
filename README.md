# Rockfile

> **A personal contact and card-making system inspired by the Rockefeller card index, powered by AI.**

<!-- Badges: left = brand color, right = neutral gray. Needs https://img.shields.io in preview. -->

![Python](https://img.shields.io/static/v1?label=Python&message=3.12&logo=python&logoColor=white&labelColor=3776AB&color=6A737D&style=for-the-badge)
![FastAPI](https://img.shields.io/static/v1?label=FastAPI&message=0.128&logo=fastapi&logoColor=white&labelColor=009688&color=6A737D&style=for-the-badge)
![Pydantic](https://img.shields.io/static/v1?label=Pydantic&message=v2&logo=pydantic&logoColor=white&labelColor=E92063&color=6A737D&style=for-the-badge)
![SQLAlchemy](https://img.shields.io/static/v1?label=SQLAlchemy&message=2.0&logo=sqlalchemy&logoColor=white&labelColor=D71F00&color=6A737D&style=for-the-badge)
![PostgreSQL](https://img.shields.io/static/v1?label=PostgreSQL&message=16&logo=postgresql&logoColor=white&labelColor=4169E1&color=6A737D&style=for-the-badge)  
![Docker](https://img.shields.io/static/v1?label=Docker&message=Compose&logo=docker&logoColor=white&labelColor=2496ED&color=6A737D&style=for-the-badge)
![Keycloak](https://img.shields.io/static/v1?label=Keycloak&message=OIDC&logo=keycloak&logoColor=white&labelColor=5B68A3&color=6A737D&style=for-the-badge)
![Poetry](https://img.shields.io/static/v1?label=Poetry&message=deps&logo=poetry&logoColor=white&labelColor=60A5FA&color=6A737D&style=for-the-badge)
![LangGraph](https://img.shields.io/static/v1?label=LangGraph&message=agents&labelColor=8e4c34&logoColor=white&color=6A737D&style=for-the-badge)
![Ollama](https://img.shields.io/static/v1?label=Ollama&message=local%20LLM&logo=ollama&logoColor=white&labelColor=111111&color=6A737D&style=for-the-badge)  
![Frontend](https://img.shields.io/static/v1?label=UI&message=HTML%20%2B%20CSS%20%2B%20JS&labelColor=c96c4b&logoColor=white&color=6A737D&style=for-the-badge)
![Status](https://img.shields.io/static/v1?label=status&message=MVP%20in%20progress&labelColor=c96c4b&logoColor=white&color=6A737D&style=for-the-badge)

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
