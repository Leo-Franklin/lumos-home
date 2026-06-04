# GitHub CI Redesign — Design Spec

**Date:** 2026-06-04
**Status:** Draft (awaiting user review)
**Author:** Claude (brainstorming session)

---

## 1. Goal

Make the GitHub CI for `lumos-home` actually run on PRs and pushes, and turn the
cross-cutting invariants in `.claude/CLAUDE.md` (API contract, lint, type-check,
test) into automated gates that fail PRs.

### Non-goals (out of scope for this change)

- Dependabot / Renovate
- Release / changelog automation
- E2E (Playwright) tests
- Docker image build / push
- New GitHub branch protection rules (this is a CI change, not a settings change)
- Strict stylistic lint rules on the frontend

---

## 2. Current state — bugs in existing CI

| # | File | Issue |
|---|------|-------|
| 1 | `ci.yml:5` | `branches: [master, ...]` — actual default is `main`, so PRs to `main` **never trigger** CI |
| 2 | `ci.yml` | No path filtering — every push (docs, screenshots, translation) builds both stacks |
| 3 | `ci.yml:48-76` | Frontend job has no lint step |
| 4 | `ci.yml` | No API contract check, even though `CLAUDE.md` §2.1 mandates schema↔api sync |
| 5 | `installer.yml:6` | Same branch mismatch (`branches: [master, ...]` implied) |
| 6 | both | No coverage reporting (deps installed in `pyproject.toml` but unused) |

---

## 3. Triggers & path filtering

### Workflow triggers (both workflows)

```yaml
on:
  push:
    branches: [main, chore/**, feature/**, fix/**, refactor/**]
  pull_request:
    branches: [main]
  workflow_dispatch:                       # manual run, useful for debugging
```

`workflow_dispatch` is additive — existing triggers keep working.

### Per-job path filter (inside `ci.yml`)

We keep a single workflow file. Per-job filtering uses
[`dorny/paths-filter`](https://github.com/dorny/paths-filter) — the standard
GitHub-native pattern when you want different jobs to react to different paths
without splitting into multiple workflow files.

| Job | Triggers when ANY of these change |
|-----|------------------------------------|
| `backend` | `backend/**`, `scripts/check_api_contract.py`, `.github/workflows/ci.yml` |
| `frontend` | `frontend/**`, `.github/workflows/ci.yml` |
| `contract` | `backend/app/schemas/**`, `frontend/src/api/**` |

A `paths-filter` step runs first (in a tiny `filter` job); the three jobs
reference its outputs via `needs.filter.outputs.<name>`. When a path
group doesn't match, the corresponding job is **skipped** (not failed), so
unchanged areas of the repo cost ~one cheap filter run.

### Concurrency

Both workflows keep `cancel-in-progress: true` so re-pushing cancels the prior
run on the same ref. This is already in `ci.yml`; add it to `installer.yml`.

---

## 4. Workflow 1 — `.github/workflows/ci.yml`

### 4.1 `backend` job

```yaml
backend:
  name: Backend · lint · typecheck · test
  runs-on: ubuntu-latest
  timeout-minutes: 15
  needs: filter
  if: needs.filter.outputs.backend == 'true'
  defaults:
    run:
      working-directory: backend
  steps:
    - uses: actions/checkout@v4
    - uses: astral-sh/setup-uv@v5
      with:
        enable-cache: true
        cache-dependency-glob: backend/uv.lock
    - run: uv sync --dev
    - run: uv run ruff check app/ tests/
    - run: uv run ruff format --check app/ tests/
    - run: uv run mypy app/
    - name: Pytest + coverage
      env:
        JWT_SECRET_KEY: test_secret_key_that_is_at_least_32_characters_long
        ADMIN_PASSWORD: testpassword_for_ci_only
        CORS_ALLOW_ORIGINS: http://localhost:5173
      run: |
        uv run pytest tests/ \
          --cov=app \
          --cov-report=xml \
          --cov-report=term-missing
    - name: Upload coverage
      if: env.CODECOV_TOKEN != ''
      uses: codecov/codecov-action@v4
      with:
        files: backend/coverage.xml
        flags: backend
        token: ${{ secrets.CODECOV_TOKEN }}
```

**Decisions:**
- `enable-cache: true` + `cache-dependency-glob` locks cache to `uv.lock`,
  matching the existing config
- Coverage upload is **gated on the secret** — without `CODECOV_TOKEN` it
  silently skips, so the workflow doesn't fail for contributors who don't
  have an account
- No pre-commit step (ruff/mypy/pytest cover the same ground)

### 4.2 `frontend` job

```yaml
frontend:
  name: Frontend · lint · test · build
  runs-on: ubuntu-latest
  timeout-minutes: 15
  needs: filter
  if: needs.filter.outputs.frontend == 'true'
  defaults:
    run:
      working-directory: frontend
  steps:
    - uses: actions/checkout@v4
    - uses: pnpm/action-setup@v4
      with:
        version: 11.0.8
    - uses: actions/setup-node@v4
      with:
        node-version: 22
        cache: pnpm
    - run: pnpm install --frozen-lockfile
    - run: pnpm lint
    - run: pnpm test
    - run: pnpm build
```

**Decisions:**
- `node-version: 22` matches `package.json` `engines.node: ">=20"` and
  matches the `installer.yml` choice
- `pnpm lint` is the new step — see §6 for the eslint config

### 4.3 `contract` job

```yaml
contract:
  name: API contract · backend schema ↔ frontend api
  runs-on: ubuntu-latest
  timeout-minutes: 5
  needs: filter
  if: needs.filter.outputs.contract == 'true'
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    - name: Run contract check
      run: python scripts/check_api_contract.py
```

**Decisions:**
- Python 3.11 matches backend's `requires-python`
- Reuses the system Python — the script only uses `ast` (stdlib)
- The script is plain Python, not pytest — a failing CI job is more visible
  than a failing test

### 4.4 `paths-filter` step (preceding all three)

```yaml
jobs:
  filter:
    runs-on: ubuntu-latest
    outputs:
      backend:  ${{ steps.filter.outputs.backend }}
      frontend: ${{ steps.filter.outputs.frontend }}
      contract: ${{ steps.filter.outputs.contract }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            backend:
              - 'backend/**'
              - 'scripts/check_api_contract.py'
              - '.github/workflows/ci.yml'
            frontend:
              - 'frontend/**'
              - '.github/workflows/ci.yml'
            contract:
              - 'backend/app/schemas/**'
              - 'frontend/src/api/**'
```

Then `backend`, `frontend`, `contract` jobs all declare
`needs: filter` (cheap) and `if: steps.filter.outputs.<name> == 'true'`.

### 4.5 Full file (pseudocode) — for reference

```yaml
name: CI

on:
  push:
    branches: [main, chore/**, feature/**, fix/**, refactor/**]
  pull_request:
    branches: [main]
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  filter:                               # see §4.4
    ...

  backend:                              # see §4.1
    needs: filter
    ...

  frontend:                             # see §4.2
    needs: filter
    ...

  contract:                             # see §4.3
    needs: filter
    ...
```

---

## 5. Workflow 2 — `.github/workflows/installer.yml`

Minimal changes:

1. **Add `main` to the push branch filter** (existing config listens to
   `master`; current default is `main`).
2. **Add concurrency** block, matching `ci.yml`.
3. **Add `cache: pnpm` to `setup-node`** (already in `ci.yml`; this file
   doesn't have it).
4. **Add `cache-dependency-glob: backend/uv.lock` to uv install** (small
   speedup; the build is on `windows-latest` so this matters less, but
   free).

Tag trigger (`on.push.tags: 'v*'`) and `workflow_dispatch` stay — they are
the intended release paths.

---

## 6. New file — `frontend/eslint.config.js`

Flat config (eslint v9 style). Loose starter, no stylistic rules, will not
shower warnings on the existing code.

```js
import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import prettier from 'eslint-config-prettier'

export default [
  js.configs.recommended,
  ...vue.configs['flat/recommended'],
  prettier,                                // must be last
  {
    ignores: ['dist/**', 'node_modules/**'],
  },
  {
    files: ['**/*.{js,vue}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        // Vitest
        describe: 'readonly', it: 'readonly', expect: 'readonly',
        beforeEach: 'readonly', afterEach: 'readonly',
        beforeAll: 'readonly', afterAll: 'readonly',
        vi: 'readonly',
        // Vue
        defineProps: 'readonly', defineEmits: 'readonly',
        defineExpose: 'readonly', withDefaults: 'readonly',
      },
    },
  },
]
```

### `frontend/.prettierrc.json`

```json
{
  "semi": false,
  "singleQuote": true,
  "trailingComma": "all",
  "printWidth": 100
}
```

(Loose defaults — matches `backend` ruff's `line-length = 100`.)

### `frontend/package.json` script additions

```json
{
  "scripts": {
    "lint": "eslint . --max-warnings 0 && prettier --check .",
    "lint:fix": "eslint . --fix && prettier --write .",
    "format": "prettier --write ."
  }
}
```

### `frontend/package.json` devDependencies additions

```json
{
  "devDependencies": {
    "@eslint/js": "^9.0.0",
    "eslint": "^9.0.0",
    "eslint-config-prettier": "^9.0.0",
    "eslint-plugin-vue": "^9.0.0",
    "prettier": "^3.0.0"
  }
}
```

**Note:** This will produce a sizeable `pnpm-lock.yaml` diff. The user has
been warned and approved.

---

## 7. New file — `scripts/check_api_contract.py`

**Purpose:** enforce `CLAUDE.md` §2.1 — a Pydantic schema change should
land in the same commit as a frontend `api/*.js` change.

**Strategy:** AST-driven extraction. Grep would over-match (comments,
strings, var names). AST gives us the actual defined class names and
field names.

### Algorithm

```
1. Parse every .py under backend/app/schemas/
   - collect: Set[Tuple[model_name, Set[field_name]]]

2. Parse every .js under frontend/src/api/
   - for each top-level export (function, const, let, var)
   - normalise to camelCase
   - collect: Set[exported_identifier]

3. Match models → exports by name (case-insensitive, snake↔camel fold)
   - for each model name, expect to find a matching export
   - missing match → ERROR
   - matched export found → OK
```

### Failure modes & messages

- **Backend-only model (no frontend export):**
  ```
  ❌ backend schema 'UserCreate' has no matching export in frontend/src/api/
     Add or update frontend/src/api/users.js (or similar).
  ```
- **Empty / missing API directory:** warning, not error (project may
  not yet have a frontend client for a brand-new model).
- **Parse error in any file:** error with file + line.

### Exit codes

- `0` — clean
- `1` — at least one missing match OR a parse error

### File layout

```
scripts/
  check_api_contract.py
  test_check_api_contract.py    # pytest tests, no pytest deps needed beyond stdlib + pyfakefs... actually just plain tests
```

Wait — the script only uses `ast` (stdlib) and `pathlib` (stdlib). Tests
should be in a place pytest finds them. To avoid pulling the script into
the backend's pytest collection (which would be a coupling), put tests in
`scripts/tests/test_check_api_contract.py` and have a small `pytest.ini`
there with `pythonpath = ../` so it can import the script.

Actually simpler: the tests can `sys.path.insert(0, ...)` in the conftest.

**Final layout:**

```
scripts/
  check_api_contract.py
  tests/
    __init__.py
    conftest.py            # adds scripts/ to sys.path
    test_check_api_contract.py
    fixtures/              # tiny synthetic backend/ and frontend/ trees
      schemas/...
      api/...
```

Run from the repo root:

```bash
cd scripts && uv run --with pytest pytest tests/ -v
```

(CI doesn't need to run the tests; this is local-validation only.
Optional: add `pytest scripts/tests/` to the backend job.)

---

## 8. Files modified / created

### Modified
- `.github/workflows/ci.yml` — rewrite
- `.github/workflows/installer.yml` — small tweaks
- `frontend/package.json` — add `lint`/`lint:fix`/`format` scripts + eslint deps
- `frontend/pnpm-lock.yaml` — regenerated by `pnpm install`

### Created
- `frontend/eslint.config.js`
- `frontend/.prettierrc.json`
- `frontend/.prettierignore`
- `scripts/check_api_contract.py`
- `scripts/tests/conftest.py`
- `scripts/tests/test_check_api_contract.py`
- `scripts/tests/fixtures/...` (synthetic)

### NOT touched
- `backend/` source, tests, `pyproject.toml`
- `installer/build.ps1`
- `docker-compose.yml`
- Root `CLAUDE.md` (the rules it already has are what we're enforcing)

---

## 9. Verification plan

After the change lands:

1. **Local quick check** (this is what I'll do before pushing):
   - `cd frontend && pnpm install && pnpm lint && pnpm test && pnpm build`
   - `cd backend && uv sync --dev && uv run ruff check app/ tests/ && uv run mypy app/ && uv run pytest tests/`
   - `python scripts/check_api_contract.py` (should be clean against current
     tree)
2. **PR test:** open a PR touching only `docs/smart_home_tool_design_v3.md`.
   Expect: `filter` job runs, all three other jobs are skipped, workflow
   exits green.
3. **PR test 2:** open a PR adding a new Pydantic model in `backend/app/schemas/`
   with **no** corresponding frontend export. Expect: `contract` job fails
   with the documented error.
4. **Tag test:** push a `v0.0.0-test` tag. Expect: `installer.yml` runs.

---

## 10. Rollout

1. Land this change as a single PR.
2. Review `pnpm-lock.yaml` diff together with the eslint config.
3. After merge, set up the `CODECOV_TOKEN` secret in repo settings **if**
   the team wants coverage tracking (optional — workflow degrades gracefully).
4. (Out of scope for this PR) Consider adding a branch protection rule
   requiring `backend`, `frontend`, `contract` jobs to pass before merge.
