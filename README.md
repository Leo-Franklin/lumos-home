# Lumos Home

> 拉丁语 *lumos* = "光"。智能家居设备管理的统一 monorepo:
> 设备发现、ONVIF 摄像头监控、NAS 录像、DLNA 投屏,
> 配合 Vue 3 仪表盘 —— 打包成单文件 Windows 安装程序。

[![CI](https://img.shields.io/github/actions/workflow/status/Leo-Franklin/lumos-home/ci.yml?branch=main&label=CI&style=flat-square)](https://github.com/Leo-Franklin/lumos-home/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue?style=flat-square)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue?style=flat-square)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/vue-3.x-brightgreen?style=flat-square)](https://vuejs.org/)

Lumos Home 把局域网设备发现、ONVIF 摄像头推流、NAS 录像、DLNA 投屏和
Vue 3 仪表盘整合到同一个 FastAPI 后端,最终以单文件 Windows 安装包的形式交付。

## ✨ 功能特性

- 🔍 设备发现与 ONVIF 探测 —— `backend/app/domain/services/scanner/`
- 📹 实时视频流 (go2rtc → HLS) —— `backend/app/domain/services/go2rtc_runner.py`
- 🎬 NAS 录像 (Frigate 风格分段) —— `backend/app/domain/services/recorder.py`
- 📺 DLNA 投屏 —— `backend/app/services/dlna_service.py`
- 📊 实时仪表盘 + WebSocket 状态推送 —— `backend/app/services/ws_manager.py`
- ⚙️ 可配置流参数面板 —— `frontend/src/components/settings/SettingsGo2RtcPanel.vue`
- 🖥️ Dark + Indigo 设计系统 —— `frontend/DESIGN.md`
- 📦 单文件 Windows 安装包 —— `installer/build.ps1`

## 📸 截图

| Dashboard | Cameras | Settings |
|---|---|---|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Cameras](docs/screenshots/cameras.png) | ![Settings](docs/screenshots/settings.png) |
| 设备状态 + 活动流 | 摄像头列表 + 实时预览 | go2rtc 流参数配置 |

> 截图目前是占位 —— 把 PNG 放到 `docs/screenshots/` 目录即可。

## 🏗️ 架构

```
                 ┌────────────┐
   RTSP / ONVIF  │  Cameras   │
                 └─────┬──────┘
                       │ RTSP
       ┌───────────────▼────────────────┐
       │  FastAPI backend (PyInstaller) │
       │   ├─ go2rtc runner (子进程)    │  ←─ HLS over :1984
       │   ├─ ffmpeg recorder (子进程)   │  ←─ segments to NAS
       │   └─ WebSocket /api/v1/ws      │
       └───────────┬────────────────────┘
                   │ REST + WS
              ┌────▼─────┐
              │ Vue 3 SPA │  (开发: Vite :5173 / 打包后: 静态挂载)
              └──────────┘
```

- 开发模式下,Vue SPA 由 Vite 跑在 :5173,把 `/api/*`、`/hls/*`、`/ws/*`
  代理到 :8000 的后端。
- 打包发布时,SPA 作为静态文件挂载在 PyInstaller bundle 内,由 FastAPI
  在单一端口同时提供 API 与前端。
- go2rtc **不是** 独立用户服务,而是由后端通过 `Go2RtcRunner` 以子进程
  方式拉起。

## 目录结构

```
lumos-home/
├── backend/                 Python 3.11 + FastAPI + SQLAlchemy 2.0 (async) + SQLite
│   ├── app/                 应用代码 (api / domain / services / models / schemas)
│   ├── tests/               Pytest 测试 (TDD —— 见 backend/.claude/CLAUDE.md)
│   ├── docs/                后端健康报告、规划、规范
│   ├── lumos-home.spec      PyInstaller 打包配置
│   └── pyproject.toml
├── frontend/                Vue 3 + Element Plus + Pinia + Vite + Vitest
│   ├── src/                 应用代码 (api / components / views / stores / router)
│   ├── tests/               Vitest 单元测试
│   ├── docs/                设计规范
│   ├── DESIGN.md            设计系统 (真相源: src/style.css)
│   └── package.json
├── installer/               Windows 安装包流水线
│   ├── build.ps1            一键打包: pnpm build → 拷贝 → PyInstaller → Inno Setup
│   ├── installer.iss        Inno Setup 脚本
│   ├── fetch-go2rtc.ps1     下载 go2rtc.exe 到 redist
│   └── redist/              内置外部工具 (ffmpeg.exe, go2rtc/, nmap/, npcap.exe)
├── docs/
│   ├── superpowers/specs/   brainstorming 流程产出的设计规范
│   ├── superpowers/plans/   writing-plans 产出的实施计划
│   └── smart_home_tool_design_v3.md   原始设计文档
├── docker-compose.yml       容器化部署 (面向 NAS)
├── .github/workflows/       统一 CI (后端 + 前端)
└── .claude/CLAUDE.md        项目级 Claude Code 指令
```

## 快速上手(开发环境)

需要 **两个终端** —— 前端是 Vite 开发服务器,会把 API/WS 请求代理到
FastAPI 后端。

**终端 1 —— 后端 (端口 8000):**
```powershell
cd D:\Project\Personal\lumos-home\backend
cp .env.example .env        # 编辑密钥 (JWT_SECRET_KEY, ADMIN_PASSWORD, ...)
uv sync --dev
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**终端 2 —— 前端 (端口 5173):**
```powershell
cd D:\Project\Personal\lumos-home\frontend
pnpm install
pnpm dev
```

浏览器打开 **<http://localhost:5173>**。Vite 会把 `/api/*`、`/hls/*`、
`/ws/*` 转发到 :8000 后端,开发阶段无需直接访问 :8000。

健康检查: `curl http://localhost:8000/api/v1/health`

> **注意:** 开发模式下后端 **不** 提供前端页面,只对外暴露 API 和
> WebSocket。UI 由 Vite 开发服务器承载。如果想看生产形态(单 exe +
> 单端口),需要走完整的安装包打包流程(见下文)。

## 技术栈

| 区域 | 选型 |
|---|---|
| 后端 | Python 3.11 · FastAPI · SQLAlchemy 2.0 async · SQLite · loguru |
| 前端 | Vue 3 · Element Plus · Pinia · Vite · Vitest |
| 流媒体 | go2rtc (子进程) · ffmpeg / ffprobe · HLS |
| 打包 | PyInstaller · Inno Setup 6 · PowerShell 7 |

## 打包 Windows 安装包

在仓库根目录 (PowerShell 7) 执行:

```bash
pwsh installer/build.ps1
# 产物: installer/output/LumosHome-Setup.exe
```

前置依赖: Node.js ≥ 20、Python 3.11 + `uv`、PyInstaller、Inno Setup 6
(`iscc` 须在 PATH 中) 以及 `installer/redist/` 下的可再发行组件。

如果 `installer/redist/go2rtc/go2rtc.exe` 缺失,运行:

```powershell
pwsh installer/fetch-go2rtc.ps1
```

也可以用打包脚本的自动拉取开关:

```powershell
pwsh installer/build.ps1 -FetchRedist
```

## 测试

后端、前端均遵循 **TDD** (强制要求见 `backend/.claude/CLAUDE.md`)。
在仓库根目录跑全部测试:

```bash
(cd backend && uv run pytest tests/ -v)
(cd frontend && pnpm test)
```

## 🛠️ 故障排查

- **运行时报 `ffprobe: not found`** —— 开发环境要求 `ffmpeg` / `ffprobe`
  在 `PATH` 中。可以把 `installer/redist/ffmpeg/` 加到 `PATH`,
  或者直接走完整安装包打包,产物里已内嵌二进制。
- **go2rtc 端口 :1984 已被占用** —— 另一个进程占用了 :1984。
  停掉占用进程,或删除 `go2rtc.json` 让后端在下次启动时重新生成。
- **PyInstaller 打包报 `ModuleNotFoundError: go2rtc_*`** —— 在 `backend/`
  下执行 `uv sync --dev` 刷新 lockfile,再重新运行
  `pwsh installer/build.ps1`。

## API 契约

- 后端通过 `/api/v1/*` 对外提供 REST + WebSocket。
- 前端 axios 客户端位于 `frontend/src/api/*.js`,统一使用
  `baseURL: '/api/v1'` (`frontend/src/api/index.js`)。
- **变更规则:** `backend/app/schemas/` 下任何 Pydantic schema 变更,
  必须在同一提交里同步更新 `frontend/src/api/*.js`。

OpenAPI 由 FastAPI 在运行时自动生成:
`http://localhost:8000/openapi.json`。前端做静态类型检查时,
在 CI 中导出该 JSON 即可 (见 `.github/workflows/ci.yml`)。

## 许可证

Apache 2.0。详见 `backend/LICENSE` 与 `frontend/LICENSE`。
