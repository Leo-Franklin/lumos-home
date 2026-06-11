# Lumos Home

> Latin *lumos* = "light". A unified monorepo for the smart home device manager:
> device discovery, ONVIF camera surveillance, NAS-backed recording, DLNA, and
> a Vue 3 dashboard — packaged as a single Windows installer.

[![CI](https://img.shields.io/github/actions/workflow/status/Leo-Franklin/lumos-home/ci.yml?branch=main&label=CI&style=flat-square)](https://github.com/Leo-Franklin/lumos-home/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue?style=flat-square)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue?style=flat-square)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/vue-3.x-brightgreen?style=flat-square)](https://vuejs.org/)

Lumos Home ties LAN device discovery, ONVIF camera streaming, NAS-backed
recording, DLNA casting, and a Vue 3 dashboard into one FastAPI backend
that ships as a single Windows installer.

## ✨ Features

- 🔍 设备发现与 ONVIF 探测 — `backend/app/domain/services/scanner/`
- 📹 实时视频流 (go2rtc → HLS) — `backend/app/domain/services/go2rtc_runner.py`
- 🎬 NAS 录制 (Frigate 风格分段) — `backend/app/domain/services/recorder.py`
- 📺 DLNA 投放 — `backend/app/services/dlna_service.py`
- 📊 实时仪表盘 + WebSocket 状态 — `backend/app/services/ws_manager.py`
- ⚙️ 可配置流参数面板 — `frontend/src/components/settings/SettingsGo2RtcPanel.vue`
- 🖥️ Dark + Indigo 设计系统 — `frontend/DESIGN.md`
- 📦 单文件 Windows 安装包 — `installer/build.ps1`

## 📸 Screenshots

| Dashboard | Cameras | Settings |
|---|---|---|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Cameras](docs/screenshots/cameras.png) | ![Settings](docs/screenshots/settings.png) |
| 设备状态 + 活动流 | 摄像头列表 + 实时预览 | go2rtc 流参数配置 |

> Screenshots are placeholders — drop your PNGs into `docs/screenshots/`.

## 🏗️ Architecture

```
                 ┌────────────┐
   RTSP / ONVIF  │  Cameras   │
                 └─────┬──────┘
                       │ RTSP
       ┌───────────────▼────────────────┐
       │  FastAPI backend (PyInstaller) │
       │   ├─ go2rtc runner (subproc)   │  ←─ HLS over :1984
       │   ├─ ffmpeg recorder (subproc) │  ←─ segments to NAS
       │   └─ WebSocket /api/v1/ws      │
       └───────────┬────────────────────┘
                   │ REST + WS
              ┌────▼─────┐
              │ Vue 3 SPA │  (dev: Vite :5173 / packaged: static mount)
              └──────────┘
```

- In dev, the Vue SPA is hosted by Vite on :5173 and proxies `/api/*`,
  `/hls/*`, `/ws/*` to the backend on :8000.
- In the packaged build, the SPA is mounted as static files inside the
  PyInstaller bundle and served by FastAPI on a single port.
- go2rtc is **not** a separate user-managed service; the backend spawns
  it as a child process via `Go2RtcRunner`.

## Repository layout

```
lumos-home/
├── backend/                 Python 3.11 + FastAPI + SQLAlchemy 2.0 (async) + SQLite
│   ├── app/                 Application code (api / domain / services / models / schemas)
│   ├── tests/               Pytest suite (TDD — see backend/.claude/CLAUDE.md)
│   ├── docs/                Backend health reports, plans, specs
│   ├── lumos-home.spec      PyInstaller build spec
│   └── pyproject.toml
├── frontend/                Vue 3 + Element Plus + Pinia + Vite + Vitest
│   ├── src/                 Application code (api / components / views / stores / router)
│   ├── tests/               Vitest unit tests
│   ├── docs/                Design specs
│   ├── DESIGN.md            Design system (source of truth: src/style.css)
│   └── package.json
├── installer/               Windows installer pipeline
│   ├── build.ps1            One-click build: pnpm build → copy → PyInstaller → Inno Setup
│   ├── installer.iss        Inno Setup script
│   ├── fetch-go2rtc.ps1     Download go2rtc.exe into redist
│   └── redist/              Bundled external tools (ffmpeg.exe, go2rtc/, nmap/, npcap.exe)
├── docs/
│   ├── superpowers/specs/   Design specs from the brainstorming workflow
│   ├── superpowers/plans/   Implementation plans produced by writing-plans
│   └── smart_home_tool_design_v3.md   Original design document
├── docker-compose.yml       Container deployment (NAS-oriented)
├── .github/workflows/       Consolidated CI (backend + frontend)
└── .claude/CLAUDE.md        Project-level Claude Code instructions
```

## Quick start (development)

You need **two terminals** — the frontend is a Vite dev server that
proxies API/WS calls to the FastAPI backend.

**Terminal 1 — backend (port 8000):**
```powershell
cd D:\Project\Personal\lumos-home\backend
cp .env.example .env        # edit secrets (JWT_SECRET_KEY, ADMIN_PASSWORD, ...)
uv sync --dev
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — frontend (port 5173):**
```powershell
cd D:\Project\Personal\lumos-home\frontend
pnpm install
pnpm dev
```

Now open **<http://localhost:5173>** in your browser. Vite will forward
`/api/*`, `/hls/*`, `/ws/*` to the backend on :8000. You do not need
to access :8000 directly during development.

Health check: `curl http://localhost:8000/api/v1/health`

> **Note:** in dev mode, the backend does **not** serve the SPA — only
> the API and WebSocket. The Vite dev server hosts the UI. If you want
> to see the production layout (one exe, one port), run the full
> installer build (see below).

## Tech stack

| 区域 | 选型 |
|---|---|
| Backend | Python 3.11 · FastAPI · SQLAlchemy 2.0 async · SQLite · loguru |
| Frontend | Vue 3 · Element Plus · Pinia · Vite · Vitest |
| Streaming | go2rtc (子进程) · ffmpeg / ffprobe · HLS |
| Packaging | PyInstaller · Inno Setup 6 · PowerShell 7 |

## Build the Windows installer

From the repo root (PowerShell 7):

```bash
pwsh installer/build.ps1
# Output: installer/output/LumosHome-Setup.exe
```

Prerequisites: Node.js ≥ 20, Python 3.11 + `uv`, PyInstaller, Inno Setup 6
(`iscc` in PATH), and the redistributables in `installer/redist/`.

If `installer/redist/go2rtc/go2rtc.exe` is missing, run
`pwsh installer/fetch-go2rtc.ps1` to download it, or use the wrapper's
auto-fetch flag:

```powershell
pwsh installer/build.ps1 -FetchRedist
```

## Testing

Both projects follow **TDD** (see `backend/.claude/CLAUDE.md` for the
mandate). Run all suites from the repo root:

```bash
(cd backend && uv run pytest tests/ -v)
(cd frontend && pnpm test)
```

## 🛠️ Troubleshooting

- **`ffprobe: not found` at runtime** — The dev environment expects
  `ffmpeg` / `ffprobe` on `PATH`. Either add `installer/redist/ffmpeg/`
  to `PATH`, or run the full installer build, which vendors the binaries.
- **go2rtc port 1984 already in use** — Another process is bound to
  :1984. Stop the conflicting process, or delete `go2rtc.json` so the
  backend regenerates it on the next start.
- **PyInstaller build fails with `ModuleNotFoundError: go2rtc_*`** —
  Run `uv sync --dev` from `backend/` to refresh the lockfile, then
  re-run `pwsh installer/build.ps1`.

## API contract

- Backend exposes REST + WebSocket under `/api/v1/*`.
- Frontend axios clients live in `frontend/src/api/*.js` and use
  `baseURL: '/api/v1'` (`frontend/src/api/index.js`).
- **Change rule:** any Pydantic schema change in `backend/app/schemas/`
  requires a matching update in `frontend/src/api/*.js` in the same commit.

OpenAPI is auto-generated by FastAPI at runtime:
`http://localhost:8000/openapi.json`. For static type-checking in the
frontend, export it during CI (see `.github/workflows/ci.yml`).

## License

Apache 2.0. See `backend/LICENSE` and `frontend/LICENSE`.
