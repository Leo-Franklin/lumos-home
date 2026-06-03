# Lumos Home — Project-Level Claude Code Instructions

This is the **root** Claude Code configuration for the Lumos Home monorepo.
Subproject-specific rules live in `backend/.claude/CLAUDE.md` and
`frontend/.claude/CLAUDE.md`.

## 1. Project at a glance

- **Backend:** Python 3.11 + FastAPI + SQLAlchemy 2.0 async + SQLite.
  See `backend/.claude/CLAUDE.md` for TDD mandate and ruff/mypy rules.
- **Frontend:** Vue 3 + Element Plus + Pinia + Vite + Vitest.
  See `frontend/DESIGN.md` for the design system (Indigo, dark, dense).
- **Packaging:** `installer/build.ps1` is the single source of truth
  for building the Windows installer.

## 2. Cross-cutting invariants

These rules apply **across all three subprojects**. Violating them is a bug:

1. **API contract is shared.** A Pydantic schema change in
   `backend/app/schemas/` requires a matching update in
   `frontend/src/api/*.js` **in the same commit**. Run a quick grep:
   `git grep -nE "field_name|enum_value" -- backend/app/schemas frontend/src/api`.
2. **Don't ship partial features.** If a router is being added in the
   backend, the corresponding `frontend/src/api/*.js` endpoint and
   `frontend/src/views/*.vue` page must be present and tested.
3. **Build artifacts are ignored, not committed.** `backend/frontend/`
   is the Vite output copied here at packaging time — never edit it
   directly. Run `pnpm --dir frontend build` to regenerate.
4. **Design tokens live in CSS variables.** See `frontend/DESIGN.md`
   §2 — never hardcode hex/rgba in components.
5. **TDD is mandatory for the backend.** See
   `backend/.claude/CLAUDE.md` §5. Frontend tests are strongly
   recommended for any new view or store.

## 3. Common tasks

| Goal | Command |
|------|---------|
| Run backend dev server | `cd backend && uv run uvicorn app.main:app --reload` |
| Run frontend dev server | `cd frontend && pnpm dev` |
| Backend tests | `cd backend && uv run pytest tests/ -v` |
| Frontend tests | `cd frontend && pnpm test` |
| Build Windows installer | `pwsh installer/build.ps1` |
| Run via Docker | `docker compose up -d` (uses `docker-compose.yml`) |

## 4. Directory map (what lives where)

```
backend/app/api/        FastAPI routers (10 endpoints, ~2600 LOC)
backend/app/domain/     Business logic (models, services, repositories)
backend/app/services/   Cross-cutting services (re-exports of domain/)
backend/app/main.py     App factory + lifespan + static-file mount (packaged only)
frontend/src/api/       Axios clients that mirror backend/app/api/
frontend/src/views/     Route components (one per major feature)
frontend/src/stores/    Pinia stores
frontend/src/router/    vue-router config
installer/              Windows packaging (PyInstaller + Inno Setup)
docs/                   Project-wide documents (design doc, plans)
```

## 5. What this monorepo is NOT

- It is **not** a published library. Don't add `setup.py` publication
  config to the root.
- It is **not** a multi-tenant SaaS. The user table is for a single
  household with shared device access.
- The frontend is **not** deployable independently. It is designed to
  be embedded in the backend's static mount (see `main.py` line ~285
  and `installer/build.ps1` Step 2).

## 6. When unsure

1. Read `docs/smart_home_tool_design_v3.md` for the original 3-week plan.
2. Read the relevant `*.claude/CLAUDE.md` for subproject rules.
3. Ask the user before adding new top-level directories or
   cross-cutting abstractions.
