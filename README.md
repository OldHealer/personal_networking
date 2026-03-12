# Rockfile

> **A personal contact and card-making system inspired by the Rockefeller card index, powered by AI.**



![Stack](https://img.shields.io/badge/stack-FastAPI%20%7C%20PostgreSQL%20%7C%20Keycloak-8e4c34?style=for-the-badge&labelColor=f7f2eb)
![Status](https://img.shields.io/badge/status-MVP_in_progress-e3b089?style=for-the-badge&labelColor=2b2a27)

---
**Rockefeller's Contact File** is an app for managing a personal file with detailed information about each person. The idea is based on the methodology of John D. Rockefeller, who kept approximately 200,000 cards with notes on contacts, meetings, promises, and connections between people.

## Features
**Contact cards** — name, contacts, date met, interests, family, notes, promises, goals
**Contact relationships** — relationship (who knows whom, family, friends, colleagues)
**Interaction history** — meetings, calls, messages with notes and promises
**Personalization** — maximum context for warm, meaningful communication

## Technologies
- **Backend**: FastAPI
- **DB**: PostgreSQL (async via SQLAlchemy 2.0)
- **Auth**: Keycloak (OIDC, JWT, multi-tenancy by tenant_id)
- **Migrations**: Alembic
- **Configuration**: pydantic-settings
- **Frontend**: Classic HTML/CSS/JS, developed as the API evolves

## Plan and architecture

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)  
  Architecture, domain model (`ContactCard`, `ContactLink`, `ContactInteraction`), layers, perspectives (AI agents, Telegram interface, mobile application).
- [`docs/DEVELOPMENT_PLAN.md`](docs/DEVELOPMENT_PLAN.md)  
  Step-by-step development plan by phase: MVP API → Connections → Search → Authorization → Frontend → AI Agent → Telegram Bot / Mini App → Mobile App.

  For each task, there's a "Progress" column—it can be used as a checklist.

## Development Status

- ✅ Basic architecture, data models, infrastructure (migrations, settings).
- ✅ First HTML pages (login, contact list, contact card).
- 🟡 CRUD API and frontend are being developed according to the plan in `DEVELOPMENT_PLAN.md`.

## License / Usage

Private project.
If you want to discuss or suggest an idea, the best way is to message us on Telegram (`https://t.me/old_healer`).