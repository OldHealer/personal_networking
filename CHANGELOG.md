# Changelog

All notable changes to this project are documented here.

---

## [Unreleased]

### Added
- `GET /api/v1/promises` — агрегированный список обещаний по всем контактам тенанта. Параметры: `open=true` (только незакрытые, по умолчанию), `direction=mine|theirs`. Каждый элемент содержит `promise_id`, `text`, `direction`, `completed_at`, `contact_id`, `contact_name`, `interaction_id`. Читает из `ContactCard.promises` (денормализованный агрегат) — один SELECT. 7 интеграционных тестов.

### Changed
- **Auth route tests:** 8 integration tests for `/api/v1/auth` — `GET /me` (authenticated + unauthenticated), `POST /register` (success, duplicate email → 409, username too long → 422, password too short → 422), `POST /login` (success, wrong credentials → 401). Keycloak calls mocked with `AsyncMock`. `auth_router` added to the shared test app in `conftest.py`.
- **Auth JS deduplication:** `getToken()`, `applyTokenFromHash()`, `handleUnauthorized()` were copy-pasted identically in `contact.js` and `contacts.js`. Moved to `ui.js` as named exports; both files now import them. Removed local `showAuthError` helpers — display logic merged into `handleUnauthorized`.
- **Agent timeouts:** `ChatOllama` now receives `timeout=AGENT__OLLAMA_TIMEOUT` (default 300 s) so a single stuck LLM call fails instead of hanging. The entire `graph.ainvoke` is wrapped in `asyncio.wait_for(timeout=AGENT__AGENT_TOTAL_TIMEOUT, default 720 s)`; on expiry the agent returns a structured error state instead of leaving the request open forever. Both values are configurable via env vars and documented in `.env.example`.
- **Input length validation:** Pydantic schemas now enforce `max_length` matching the DB `String(N)` constraints (`full_name`/`email`/`username` → 255, `phone`/`channel` → 50, `relationship_type` on contacts → 20, on links → 50, `family_status` → 100, `password` → 128). `Text` columns are intentionally unbounded. Applies to `contacts.py`, `auth.py`, `admin_users.py` schemas.
- **`LOCAL_DEV` flag:** was a hardcoded `bool = False` in `settings.py`. Now read from the `LOCAL_DEV` environment variable (`"1"/"true"/"yes"` → `True`). Set it in the shell or IDE run config when working locally against `.env.local`; production deployments need no change. Added commented example to `.env.example`.
- **ORM lazy loading:** all collection relationships (`Tenant.users`, `Tenant.contacts`, `ContactCard.family_members/interactions/links_from/links_to`) changed from `lazy="selectin"` to `lazy="raise"`. Previously every `GET /contacts/{id}` and list query fired 4–6 extra SELECTs for collections that are never accessed via ORM (all data is fetched through explicit service queries). With `lazy="raise"` accidental attribute access raises an explicit error instead of silently issuing a query.

### Fixed
- **Alembic migrations at startup:** `run_migrations()` now runs alembic in a `ThreadPoolExecutor` so `asyncio.run()` inside `env.py` doesn't conflict with the FastAPI lifespan event loop. `alembic/env.py` no longer passes the DB URL through `config.set_main_option` (ConfigParser breaks on `%` in passwords) — uses a `sqlalchemy.engine.URL` object directly instead. `db_bootstrap.py` calls `alembic.command.upgrade` via Python API instead of `python -m alembic` subprocess.
- **Security (ops):** removed `:-<default>` fallbacks for all password variables in `docker-compose.yml` (`DATABASE__DB_PASSWORD`, `KEYCLOAK_DB_PASSWORD`, `KEYCLOAK_ADMIN_PASSWORD`). Replaced with `${VAR:?message}` — compose refuses to start if a password is missing, instead of silently booting the stack with the fallback values that used to leak via `git show`. Usernames / DB names kept their defaults (not secrets). Introduced `.env.example` with all required keys and a `python -c "import secrets; ..."` hint for `TOKEN__SECRET_KEY`; `.gitignore` updated to un-ignore `.env.example`.
- **Security:** tenant isolation bypass in `GET/PATCH/DELETE /api/v1/contacts/{id}` — endpoints accepted any contact UUID without checking `tenant_id`, allowing cross-tenant reads/updates/deletes. Now `ContactService.get_contact/update_contact/delete_contact` require `tenant_id` and return 404 for contacts of other tenants. `contacts_tools.contacts_get` (agent tool) updated accordingly. 3 integration tests added (`test_get/update/delete_contact_tenant_isolation`).
- **Security:** tenant isolation bypass in `GET /api/v1/contacts/{id}/links` — `list_links_for_contact` received `tenant_id` but ignored it, so any authenticated user could read another tenant's links. Now runs `_ensure_contact_belongs_to_tenant` (same path as create/update/delete) and filters `ContactLink.tenant_id`. Integration test added (`test_list_links_tenant_isolation`).
- **Data integrity:** duplicate `ContactLink` entries were silently allowed between the same pair of contacts with the same `relationship_type`. Added `UniqueConstraint(contact_id_a, contact_id_b, relationship_type)` (name `uq_contact_links_pair_type`). For symmetric links (`is_directed=False`) service normalizes pair order so reverse-direction duplicates (B→A) collide with existing A→B. `IntegrityError` on create/update is mapped to HTTP 409. 3 integration tests added (same-direction dup, undirected reverse-order dup, different `relationship_type` still allowed).

### Added
- Alembic initialized with async template. Two migrations: `8dc7dd5600f3` baseline schema (all tables + indexes, reverse-engineered from current models against an empty DB) and `e8821371d1f5` add `uq_contact_links_pair_type`. `alembic/env.py` reads DB URL from `settings.config`, targets `Base.metadata`, enables `compare_type=True`. Existing production DB was stamped with the baseline revision and upgraded; fresh installs get everything via `alembic upgrade head` (already wired in `lifespan` through `utils.db_bootstrap.run_migrations`).
- Dev dependency: `alembic ^1.13`. Relaxed `pytest`/`pytest-asyncio` upper bounds so the lock file keeps the newer major versions (pytest-asyncio 1.x is required for `asyncio_default_test_loop_scope`).
- Sidebar on contacts page: upcoming birthdays (top 3, sorted by days remaining), stale contacts (45+ days, random order), and contact stats widget
- Stats endpoint `GET /api/v1/contacts/stats` — GROUP BY relationship_type, returns total + breakdown; 3 integration tests (empty, grouping, tenant isolation)
- Two-mode search card: "По имени" (real-time filter) and "По содержимому" (full-text), with segmented switcher; removed duplicate search from list header
- Unique badge color per relationship type (11 types, light + dark theme)
- Right sidebar layout on contacts page (1fr + 260px grid, sticky on wide screens; stacks horizontally under the list on ≤1024px, vertically on ≤560px)
- Container width increased from 1100px to 1400px
- Quick-add contact form made compact (inline flex row, matches AI agent card style)
- Uniform button height on contact detail page (matching "Редактировать" size)
- Amber button color theme (#b08040), card hover border matches button color
- Filter row changed from flex to CSS grid (4 equal columns) to match contact card grid width
- Full-text search endpoint `GET /api/v1/search?q=` — tsvector (`russian`) + GIN indexes across `contact_cards` (name, address, ambitions, hobbies, interests, goals) and `contact_interactions` (notes, promises, mentions). Returns ranked hits with `ts_headline` snippets highlighted via `<mark>`. Supports `websearch_to_tsquery` syntax (quotes, OR). Tenant-isolated.
- UI: "Глубокий поиск" card on contacts page — debounced input hits `/api/v1/search`, renders separate lists of matched contacts and interactions with highlighted snippets; each hit links to the contact page.
- Generated tsvector columns `search_tsv` + GIN indexes created via idempotent bootstrap on app startup (`utils/search_bootstrap.py`) — normalizes JSON fields through `jsonb::text` to avoid `\uXXXX` tokenization of Cyrillic.
- 7 integration tests for `/api/v1/search` (contact fields, array JSON fields, interaction notes, empty query, tenant isolation, ranking, limit)
- Server-side search `?q=` in `GET /api/v1/contacts` — ILIKE by `full_name` and `email`
- Debounced search input (300ms) in contacts list UI — no longer limited to 50 loaded records
- Filter `?last_contact_before=N` in `GET /api/v1/contacts` — "давно не общались N дней" (falls back to `created_at` when no interactions)
- Filter `?relationship_type=colleague` in contacts list
- Filter `?has_birthday_soon=N` — ДР в ближайшие N дней (day-of-year ring arithmetic, корректно работает через границу года)
- Sort `?sort=last_contact_at` with NULLS LAST (контакты без встреч уезжают в конец)
- UI dropdowns on contacts page: "Тип отношений", "Давно не общались" (7/30/90/180), "Дни рождения" (7/14/30/90), "По дате последней встречи" в сортировке
- Integration tests (35 total): contacts CRUD + search + filters (stale/relationship/birthday) + sort + tenant isolation, links CRUD, interactions CRUD + promises aggregation and completion
- `tests/` directory with `conftest.py` — isolated `rockfile_test` DB, mocked auth via `dependency_overrides`, httpx `AsyncClient` over `ASGITransport`
- Dev dependencies: `pytest`, `pytest-asyncio` (configured in `pyproject.toml`)

### Changed
- DEVELOPMENT_PLAN.md: marked completed phases (0–5, frontend), added Phase 8 Tests, updated priorities
- ARCHITECTURE.md: updated directory structure to match reality, updated tech stack (LangGraph, FastMCP, Ollama, dark theme), fixed promise direction field (`mine/theirs`)
- CLAUDE.md created in project root with stack, conventions, and pre-commit checklist
- Global ~/.claude/CLAUDE.md extended with communication rules and security guards
- Memory files added: user profile, project context

## [0.3.0] — 2026-04-22

### Added
- Dark/light theme toggle with anti-FOUC inline script across all pages
- `initTheme()` / `setupThemeToggle()` in `ui.js`, wired to every page
- `showToast()` in `ui.js` — animated error/info popup (top-right, auto-dismiss 6s)
- Toast replaces raw JSON error output on login/register; 422 validation errors are parsed into human-readable Russian messages
- Contact detail page: edit and delete for links (PATCH / DELETE `/contacts/{id}/links/{link_id}`)
- Contact detail page: edit and delete for interactions
- Promise direction tracking — "mine" / "theirs" labels with colored badges
- Channel field on interactions changed to a select with emoji options
- Relationship type badges on contact cards with relative last-seen time
- Expanded relationship type options (professional / personal / family groups)
- Tooltip `ⓘ` on "Направленная связь" checkbox explaining the concept
- Auto-resize textareas — height grows with content, no manual drag needed
- `AgentSettings` added to `settings.py`; agent config migrated from `os.getenv` to Pydantic settings
- New backend files: `mcp_server.py`, `contacts_tools.py`, `contact_interactions.py`, `contact_links.py`, `interactions_service.py`, `links_service.py`, `strip-token-from-url.js`

### Changed
- `index.html` redesigned: compact hero with eyebrow label, feature cards with icons, benefits grid
- `login.html` redesigned: single card with Login / Register tabs, no page reload on switch
- Section vertical padding reduced (`3.5rem → 2.5rem`), hero padding reduced (`5rem 0 8rem → 3rem 0 3.5rem`)
- Hero background changed from mountains SVG to clean warm gradient with decorative radial glow
- `prepare_meeting_agent.py` refactored: LLM module-level cache, conditional error routing in LangGraph, `CallToolResult.data` fix
- Dark theme overhauled: fixed hero, `.section-muted`, `.auth-card`, `.form-subtitle`, search inputs, selects, buttons contrast

### Fixed
- Keycloak port conflict: `8181 → 8282` in `docker-compose.yml`
- `tenant_id` unexpected keyword argument in `contacts_tools.py`
- `CallToolResult` not subscriptable — switched from `result[0]` to `result.data`
- Render-blocking Google Fonts `<link>` removed — was blocking page load in Docker (no internet)
- Delete button text invisible in dark theme (was dark red `#b42318` on dark background)

---

## [0.2.0] — 2026-04-15

### Added
- Multi-step Task Agent (`prepare_meeting_agent.py`) using LangGraph
- MCP server integration for agent tools

### Changed
- Contact card UI: basic layout and form fields

---

## [0.1.0] — 2026-04-10

### Added
- Initial project structure: FastAPI backend, Keycloak auth, SQLAlchemy async
- Contacts CRUD with pagination and sorting
- Contact detail page with interactions and links
- Docker Compose setup
