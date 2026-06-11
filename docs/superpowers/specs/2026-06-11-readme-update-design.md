# README Update — Design

- **Date:** 2026-06-11
- **Status:** Draft (pending user review)
- **Scope:** Root `README.md` only. No source code, no installer, no docs/ subfolders changed.

## 1. Problem

`README.md` was last meaningfully updated for the M3/M4-era feature set. Two
concrete defects and one content gap have accumulated since:

1. **Defect — wrong path.** Quick start commands point at
   `D:\Project\Demo\lumos-home\...`, the legacy project location. The current
   working copy lives at `D:\Project\Personal\lumos-home\...`. A new contributor
   copy-pasting the snippet will fail at `cd`.
2. **Defect — wrong script name.** The README references
   `installer/fetch-redist.ps1`, but that file does not exist. The actual
   fetchers in the repo are `installer/fetch-go2rtc.ps1` and the redist
   assets are vendored under `installer/redist/`. The build wrapper
   `installer/build.ps1 -FetchRedist` is the supported entry point.
3. **Gap — go2rtc live streaming absent.** The largest feature added since the
   last README revision is the go2rtc-powered HLS pipeline
   (`backend/app/domain/services/go2rtc_{adapter,proxy,runner}.py`,
   `frontend/src/components/LivePlayer.vue`,
   `frontend/src/components/settings/SettingsGo2RtcPanel.vue`,
   `docs/go2rtc-live-streaming-plan.md`). A public-facing README that omits
   the headline feature makes the project look stale.
4. **Gap — no features / no screenshots / no architecture overview / no tech
   stack / no troubleshooting.** First-time visitors have no fast path to
   "what does this do" or "what do I do when X breaks".

## 2. Goals & non-goals

### Goals
- Fix both defects so the Quick start and Build sections are copy-paste runnable.
- Surface go2rtc, recording, DLNA, WebSocket, settings, and packaging as
  named features with code-path pointers.
- Add a Screenshots placeholder block, a text-mode Architecture diagram, a
  Tech stack table, and a small Troubleshooting section.
- Keep the existing six-section skeleton; insert new sections in front of
  or alongside existing ones — do not reshuffle.
- Public-GitHub tone: badges, complete intro, but no marketing copy, no
  roadmap, no contributing manifesto.

### Non-goals
- Do not rewrite the README end-to-end (out of scope per user choice A).
- Do not generate, fetch, or commit real screenshots. Image paths are
  placeholders only; the file `docs/screenshots/*.png` will not exist.
- Do not edit `backend/README.md`, `frontend/README.md`, or any file under
  `docs/` other than this spec.
- Do not introduce new tooling, badges services beyond shields.io, or
  external image hosts.

## 3. Target audience

Primary: open-source visitors landing on the GitHub repo page. They want to
know (a) what it is, (b) what it does, (c) what stack it uses, (d) how to
run it. Secondary: the project author returning after months away.

## 4. Final section structure

```
# Lumos Home                  ← title + 1-paragraph intro + 4 shields.io badges
## ✨ Features                ← NEW
## 📸 Screenshots             ← NEW (3 placeholder images)
## 🏗️ Architecture            ← NEW (ASCII diagram + 3-line note)
## Repository layout          ← preserved, plus 1 line for new dirs
## Quick start (development)  ← defect fixes applied
## Tech stack                 ← NEW (4-row table)
## Build the Windows installer← defect fix applied
## Testing                    ← preserved
## 🛠️ Troubleshooting         ← NEW (3 entries)
## API contract               ← preserved
## License                    ← preserved
```

Section count goes from 6 to 10. Order is chosen so a first-time visitor
reads: what it is → features → pictures → architecture → repo map → run it
→ build it → troubleshoot. The original "Repository layout → Quick start"
order is preserved as the centre of gravity.

## 5. Section-by-section spec

### 5.1 Header
- Title line unchanged: `# Lumos Home`.
- Latin *lumos* epigraph unchanged.
- Insert one line of 4 shields.io badges after the epigraph:
  `CI`, `License (Apache 2.0)`, `Python 3.11+`, `Vue 3`. All endpoints use
  the static shields.io URL — no build step, no rate-limit risk.
- Follow with a 2–3 sentence intro paragraph: what the project is, who it
  is for, and the headline stack line.

### 5.2 ✨ Features (new)
Eight bullets, each one line + module path in backticks:

| Bullet | Module path |
|---|---|
| 🔍 设备发现与 ONVIF 探测 | `backend/app/domain/services/scanner/` |
| 📹 实时视频流 (go2rtc → HLS) | `backend/app/domain/services/go2rtc_runner.py` |
| 🎬 NAS 录制 (Frigate 风格分段) | `backend/app/domain/services/recorder.py` |
| 📺 DLNA 投放 | `backend/app/services/dlna_service.py` |
| 📊 实时仪表盘 + WebSocket 状态 | `backend/app/services/ws_manager.py` |
| ⚙️ 可配置流参数面板 | `frontend/src/components/settings/SettingsGo2RtcPanel.vue` |
| 🖥️ Dark + Indigo 设计系统 | `frontend/DESIGN.md` |
| 📦 单文件 Windows 安装包 | `installer/build.ps1` |

No emojis in the README outside this section. No "Coming soon" entries.

### 5.3 📸 Screenshots (new)
Three columns table. Each cell: image markdown with a relative path under
`docs/screenshots/`, plus a one-line caption.

| Dashboard | Cameras | Settings |
|---|---|---|
| `![Dashboard](docs/screenshots/dashboard.png)` | `![Cameras](docs/screenshots/cameras.png)` | `![Settings](docs/screenshots/settings.png)` |
| 设备状态 + 活动流 | 摄像头列表 + 实时预览 | go2rtc 流参数配置 |

A blockquote immediately under the table states:

> Screenshots are placeholders — drop your PNGs into `docs/screenshots/`.

The `docs/screenshots/` directory is intentionally not created; GitHub will
render the images as broken links until the user supplies the files. This
is a documented placeholder, not a bug.

### 5.4 🏗️ Architecture (new)
A single ASCII diagram (≤ 18 lines) showing three primary links:

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

Followed by 3 plain-text notes:
1. In dev, the Vue SPA is hosted by Vite on :5173 and proxies `/api/*`,
   `/hls/*`, `/ws/*` to the backend on :8000.
2. In the packaged build, the SPA is mounted as static files inside the
   PyInstaller bundle and served by FastAPI on a single port.
3. go2rtc is **not** a separate user-managed service; the backend spawns
   it as a child process via `Go2RtcRunner`.

### 5.5 Repository layout (preserved + minor additions)
Insert two new lines into the existing tree:

- `docs/superpowers/specs/ Design specs from the brainstorming workflow`
- `docs/superpowers/plans/ Implementation plans produced by writing-plans`

Otherwise the tree is unchanged. No reordering.

### 5.6 Quick start (development) — defect fixes
Three edits, no other changes:

| Line | Old | New |
|---|---|---|
| `cd backend` | `D:\Project\Demo\lumos-home\backend` | `D:\Project\Personal\lumos-home\backend` |
| `cd frontend` | `D:\Project\Demo\lumos-home\frontend` | `D:\Project\Personal\lumos-home\frontend` |
| Build section step 3 | `pwsh installer/fetch-redist.ps1` | `pwsh installer/fetch-go2rtc.ps1` (and a one-line note that this is only needed if `installer/redist/go2rtc/go2rtc.exe` is missing) |

The two-terminal flow, the dev-server ports, the `curl` health check, and
the "Vite hosts the UI in dev" note are preserved verbatim.

### 5.7 Tech stack (new)
Single markdown table with 4 rows:

| 区域 | 选型 |
|---|---|
| Backend | Python 3.11 · FastAPI · SQLAlchemy 2.0 async · SQLite · loguru |
| Frontend | Vue 3 · Element Plus · Pinia · Vite · Vitest |
| Streaming | go2rtc (子进程) · ffmpeg / ffprobe · HLS |
| Packaging | PyInstaller · Inno Setup 6 · PowerShell 7 |

No version pins beyond the minimum (Python 3.11+).

### 5.8 Build the Windows installer — defect fix
One edit:
- Change the second `pwsh installer/fetch-redist.ps1` snippet to a one-line
  hint: "If `installer/redist/go2rtc/go2rtc.exe` is missing, run
  `pwsh installer/fetch-go2rtc.ps1`."
- Keep the `-FetchRedist` build flag mention (it still works on the wrapper
  script for the other redist assets).

The prerequisites paragraph (Node ≥ 20, Python 3.11 + uv, PyInstaller, Inno
Setup 6) is preserved.

### 5.9 Testing (preserved)
No changes. TDD reference to `backend/.claude/CLAUDE.md` stays.

### 5.10 🛠️ Troubleshooting (new)
Three entries, each ≤ 4 lines:

1. **`ffprobe: not found` at runtime** — The dev environment expects
   `ffmpeg`/`ffprobe` on PATH. Either add `installer/redist/ffmpeg/` to
   PATH, or run the full installer build, which vendors the binaries.
2. **go2rtc port 1984 already in use** — Another process is bound to :1984.
   Edit `go2rtc.json` (regenerated by the backend on next start) or stop
   the conflicting process. The backend will respawn go2rtc on save.
3. **PyInstaller build fails with `ModuleNotFoundError: go2rtc_*`** — Run
   `uv sync --dev` from `backend/` to refresh the lockfile, then re-run
   `pwsh installer/build.ps1`.

No "open an issue" boilerplate.

### 5.11 API contract (preserved)
No changes. The OpenAPI pointer and the "schema change ⇒ API client change"
rule stay.

### 5.12 License (preserved)
No changes. Apache 2.0, pointing at `backend/LICENSE` and `frontend/LICENSE`.

## 6. Out-of-scope follow-ups (mentioned, not done)

These are explicitly **not** part of this spec and should be tracked
separately if the user wants them later:

- Real screenshots under `docs/screenshots/`.
- A `CONTRIBUTING.md` with PR/issue conventions.
- A `CODE_OF_CONDUCT.md`.
- An architecture decision record (ADR) folder.
- A `docs/adr/` series capturing the go2rtc / recording / discovery design
  rationale beyond `smart_home_tool_design_v3.md`.

## 7. Verification

After the edit, the following must all be true:

1. `git diff README.md` shows changes **only** in `README.md` at the repo
   root. No incidental whitespace or end-of-file churn.
2. Every relative link in the rewritten README resolves to an existing file
   in the working tree: `./backend`, `./frontend`, `./installer`,
   `./docs/smart_home_tool_design_v3.md`, `./.github/workflows/ci.yml`,
   `./backend/.claude/CLAUDE.md`, `./frontend/DESIGN.md`, and each module
   path listed in the Features section.
3. Both defect fixes are visible: search the diff for the old strings
   (`D:\Project\Demo\`, `fetch-redist.ps1`) — both must return zero hits in
   the new file.
4. Markdown lint sanity: no unclosed code fences, no orphan `|` in tables.
5. README total length grows from ~110 to ~200 lines (±30). Anything
   shorter means a section was dropped; anything longer means scope creep.

## 8. Risks

- **Broken image placeholders.** GitHub will render three broken image
  icons in the Screenshots section. Mitigated by the blockquote hint and
  the user choosing "placeholders only" explicitly.
- **Stale module paths.** The Features section hard-codes paths like
  `backend/app/domain/services/go2rtc_runner.py`. If any of those files
  move, the README lies. Mitigated by the new section being short and
  trivially editable; we do not promise it stays in lockstep with the code.
- **Path portability.** The Quick start is hard-coded to a Windows path
  under `D:\Project\Personal\...`. This is acceptable because the project
  ships as a Windows installer first; a Linux/macOS dev path can be added
  in a follow-up spec if needed.

## 9. Open questions

None. All clarifying questions answered by the user prior to this spec:

| Question | Answer |
|---|---|
| README change scope | Fix defects + fill critical content (option A) |
| Audience | Public GitHub |
| Screenshots | Placeholders only, fill in later |
