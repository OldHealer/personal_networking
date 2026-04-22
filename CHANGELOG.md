# Changelog

All notable changes to this project are documented here.

---

## [Unreleased]

### Added
- Server-side search `?q=` in `GET /api/v1/contacts` — ILIKE by `full_name` and `email`
- Debounced search input (300ms) in contacts list UI — no longer limited to 50 loaded records
- Filter `?last_contact_before=N` in `GET /api/v1/contacts` — "давно не общались N дней" (falls back to `created_at` when no interactions)
- UI dropdown "Давно не общались" on contacts page: 7/30/90/180 days presets
- Integration tests (31 total): contacts CRUD + search + stale filter + tenant isolation, links CRUD, interactions CRUD + promises aggregation and completion
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
