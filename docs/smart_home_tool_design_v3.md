# 智能家居设备管理与视频备份工具 — 设计文档 v3

> **日期**：2026-04-24
> **作者**：技术评审优化
> **基线**：v2 方案评审后重写
> **目标环境**：家庭局域网 (LAN)
> **前端**：Vue 3 + Vite
> **后端**：Python 3.11 + FastAPI

---

## 0. v2 → v3 评审变更记录

| # | v2 问题 | v3 修正 | 原因 |
|:--|:---|:---|:---|
| 1 | `onvif-zeep` 是同步库，代码标了 `async` 但实际会阻塞事件循环 | 所有 ONVIF/nmap 调用显式 `run_in_executor` 包装 | FastAPI 的 async 路由中调用同步阻塞代码会卡住整个事件循环 |
| 2 | FFmpeg 进程无监控，崩溃后无人感知 | 增加 `RecordingMonitor` 后台任务，轮询进程状态 | 摄像头断流、磁盘满等场景 FFmpeg 会静默退出 |
| 3 | `APScheduler 4.0.0a5` (alpha) 用于生产 | **降级为 APScheduler 3.10.x (stable)**，4.x 等正式发布再迁移 | alpha 版本 API 不稳定，文档不全，生产环境不宜使用 |
| 4 | `ffmpeg-python` 在依赖中但代码实际用 `subprocess` | 移除 `ffmpeg-python`，统一用 `subprocess` 调用 FFmpeg CLI | 依赖和实现不一致，`subprocess` 对 FFmpeg 控制力更强 |
| 5 | WebSocket `ConnectionManager.broadcast` 遍历时可能并发修改列表 | 改用 `set` + 广播时拷贝快照 | 并发修改 list 导致 `RuntimeError` 或漏推 |
| 6 | 前端原生 WebSocket 无重连机制 | 引入指数退避重连逻辑 | 网络抖动、后端重启后前端永久断开 |
| 7 | API 无分页，录像列表可能返回海量数据 | 所有列表接口增加分页参数 `page` + `page_size` | 运行半年后录像表可达数万条 |
| 8 | 提到"本地 JWT"但无设计 | 补全 JWT 认证流程 + 中间件 | v2 提了安全但没落地 |
| 9 | 缺少系统健康检查 | 增加 `GET /health` 端点 | Docker 健康检查 + 前端连接状态判断 |
| 10 | NAS 同步判断逻辑脆弱（`dest.drive == src.drive`） | 改为配置驱动：环境变量 `NAS_MODE=mount\|smb` 显式指定 | 文件系统判断不可靠，不如让用户明确声明 |
| 11 | `docker-compose` 中 `version: "3.9"` 已废弃 | 移除 version 字段（Docker Compose V2 已不需要） | Docker 官方自 2023 起不再使用 version 字段 |
| 12 | 无视频回放服务策略 | 增加基于 Range 请求的 MP4 渐进式回放 + 可选 HLS 分片 | 前端播放器需要后端配合提供可寻址的视频流 |
| 13 | 开发周期 6-9 天过于乐观 | 调整为 3 周（含联调和硬件适配），标注风险点 | ONVIF 兼容性调试、Docker 网络问题通常耗时超预期 |
| 14 | `schedules` 表缺少时间戳 | 补充 `created_at` / `updated_at` | 排查问题时需要知道计划何时创建/修改 |
| 15 | 无运行日志方案 | 增加 `loguru` 结构化日志 + 文件轮转 | Docker 容器日志和文件日志双通道 |

---

## 1. 项目概述

### 1.1 核心需求

1. **设备发现**：ARP 扫描局域网，识别在线设备的 IP、MAC、厂商。
2. **设备管理**：手动标记设备类型（摄像头/电脑/手机/热水器），保存备注名称。
3. **摄像头接入**：通过 ONVIF 发现摄像头能力，通过 RTSP 拉流录制。
4. **视频备份**：按计划将录制片段自动同步到绿联 NAS 指定目录。
5. **Web 控制台**：Vue.js 单页应用，管理设备、查看录像、配置计划任务。

### 1.2 已知硬件环境

| 设备 | 型号/说明 |
|:---|:---|
| 摄像头 | TP-Link IPC682F-A4（支持 ONVIF + RTSP） |
| NAS | 绿联 UGREEN NAS（支持 SMB/WebDAV/Docker） |
| 运行平台 | NAS 的 Docker 环境（推荐）或局域网内任意 Linux/Windows 主机 |

### 1.3 非功能需求

| 维度 | 指标 |
|:---|:---|
| 可用性 | 后端崩溃自动重启（Docker `restart: unless-stopped`） |
| 存储 | 单路 1080P H.264 约 1-2 GB/小时，按需配置保留天数 |
| 延迟 | 设备扫描 < 10s，ONVIF 探测 < 5s，WebSocket 推送 < 1s |
| 并发 | 支持同时录制 1-4 路摄像头（受 NAS CPU 和磁盘 IO 限制） |

---

## 2. 技术选型

### 2.1 后端

| 层级 | 选择 | 理由 |
|:---|:---|:---|
| 语言 | Python 3.11+ | 网络/IoT 生态最完整，`onvif-zeep`、`nmap`、`scapy` 均有成熟库 |
| Web 框架 | FastAPI | 原生 async，自动 OpenAPI 文档，WebSocket 原生支持 |
| ORM | SQLAlchemy 2.0 (async) | 配合 FastAPI async 路由，避免阻塞 |
| 数据库 | SQLite | 家庭场景足够，零运维，文件即数据库 |
| 任务调度 | **APScheduler 3.10.x** | 稳定版本，支持动态增删任务，API 控制无需重启 |
| 设备扫描 | scapy（ARP） + python-nmap（端口） | scapy 做 L2 快速发现，nmap 做精细端口探测 |
| MAC 厂商识别 | mac-vendor-lookup | 离线 OUI 数据库，识别 TP-Link/Apple/小米等 |
| 摄像头协议 | onvif-zeep (ONVIF) + FFmpeg CLI (RTSP) | ONVIF 管理，FFmpeg 录制（subprocess 直接调用） |
| NAS 写入 | 文件系统直写（Docker挂载）/ smbprotocol（降级） | 由 `NAS_MODE` 环境变量显式控制 |
| 实时通信 | FastAPI WebSocket | 推送设备在线状态变化、录制事件 |
| 配置管理 | python-dotenv + Pydantic Settings | 凭据走环境变量，不硬编码 |
| 日志 | loguru | 结构化日志，支持文件轮转和控制台彩色输出 |
| 认证 | python-jose (JWT) + passlib | 局域网内轻量认证，防止未授权访问 |

### 2.2 前端

| 层级 | 选择 | 理由 |
|:---|:---|:---|
| 框架 | Vue 3 (Composition API) + Vite | 用户指定 |
| 状态管理 | Pinia | Vue 3 官方推荐，比 Vuex 简洁 |
| 路由 | Vue Router 4 | 标准方案 |
| UI 组件库 | Element Plus | 中文文档完善，表格/表单组件丰富，适合管理后台 |
| HTTP 客户端 | Axios | 拦截器统一处理 token 刷新和错误码 |
| WebSocket | 原生 WebSocket + 自定义重连封装 | 指数退避重连，断线自动恢复 |
| 视频播放 | Video.js | 支持 MP4 渐进式播放 + HLS 流，功能完善 |

### 2.3 关于 FFmpeg 的说明

本项目使用 `subprocess` 直接调用系统安装的 FFmpeg CLI，**不使用** `ffmpeg-python` 库。原因：

1. FFmpeg CLI 的参数文档最全，社区答案可直接复用。
2. `subprocess` 提供对进程生命周期的完整控制（启动、监控、信号终止）。
3. `ffmpeg-python` 只是参数拼接器，增加了一层抽象但不增加能力。

Docker 镜像需包含 FFmpeg：`apt-get install -y ffmpeg` 或使用 `linuxserver/ffmpeg` 基础镜像。

---

## 3. 系统架构

### 3.1 整体架构图

```
┌──────────────────────────────────────────────────────────────┐
│                     浏览器 (Vue 3 SPA)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ 设备列表  │ │ 摄像头   │ │ 录像库   │ │ 任务计划/设置    │ │
│  │ /devices │ │ /cameras │ │/recordings│ │ /schedule|/settings│
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───────┬──────────┘ │
│       └─────────────┴────────────┴───────────────┘            │
│                REST API + WebSocket + JWT                      │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                    后端 (FastAPI + Uvicorn)                    │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Scanner     │  │  Camera      │  │  NAS Syncer  │        │
│  │  模块         │  │  模块         │  │  模块         │        │
│  │ ARP(scapy)   │  │ ONVIF(zeep)  │  │ mount / SMB  │        │
│  │ Port(nmap)   │  │ RTSP(FFmpeg) │  │              │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│         │                 │                  │                │
│  ┌──────▼─────────────────▼──────────────────▼───────┐       │
│  │  APScheduler 3.x (定时: 扫描 / 录制 / 清理)        │       │
│  └───────────────────────────────────────────────────┘       │
│  ┌───────────────────────────────────────────────────┐       │
│  │  RecordingMonitor (FFmpeg 进程看门狗)               │       │
│  └───────────────────────────────────────────────────┘       │
│  ┌───────────────────────────────────────────────────┐       │
│  │  SQLite + SQLAlchemy async (数据持久化)             │       │
│  └───────────────────────────────────────────────────┘       │
│  ┌───────────────────────────────────────────────────┐       │
│  │  JWT AuthMiddleware (认证层)                        │       │
│  └───────────────────────────────────────────────────┘       │
└──────────────────────────────┬───────────────────────────────┘
                               │  局域网
            ┌──────────────────┼──────────────────┐
            │                  │                  │
  ┌─────────▼────────┐ ┌──────▼────────┐ ┌───────▼───────┐
  │  TP-Link 摄像头   │ │  绿联 NAS     │ │  其他设备      │
  │  ONVIF:2020      │ │  存储目标      │ │  手机/电脑     │
  │  RTSP:554        │ │  Docker宿主    │ │               │
  └──────────────────┘ └───────────────┘ └───────────────┘
```

### 3.2 核心数据流

**设备扫描流程：**
```
定时触发(每60s) / 手动触发(API)
  → ARP 扫描 (scapy, run_in_executor) → 获取 IP + MAC 列表
  → MAC OUI 查厂商 (离线数据库)
  → 与数据库已知设备比对 → 计算 diff (新上线/已离线)
  → 可选: nmap 探测新设备端口 (554/2020/80)，耗时较长仅对新设备执行
  → 批量更新数据库
  → WebSocket 广播变化事件到所有前端客户端
```

**视频录制流程：**
```
APScheduler 触发 / 手动 API 触发
  → 检查摄像头在线状态 (ONVIF GetDeviceInformation 或直接 TCP 连接测试)
  → 启动 FFmpeg 子进程: rtsp → mp4 (codec copy, TCP传输, 固定时长分片)
  → RecordingMonitor 后台协程每 10s 检查进程状态
     ├── 正常运行: 无操作
     ├── 正常结束(时长到达): 触发同步 → NAS 目录, 写录像元数据, 清理临时文件
     └── 异常退出: 记录错误日志, WebSocket 通知前端, 按策略决定是否重试
```

**视频回放流程：**
```
前端 Video.js 请求 GET /api/v1/recordings/{id}/stream
  → 后端读取 NAS 上的 MP4 文件
  → 支持 HTTP Range 请求 (支持拖动进度条)
  → 返回 206 Partial Content
```

---

## 4. 项目目录结构

```
smart-home-tool/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口, lifespan 管理启停
│   │   ├── config.py               # Pydantic Settings, 读取 .env
│   │   ├── database.py             # SQLAlchemy async engine + session
│   │   ├── auth.py                 # JWT 生成/验证 + 登录接口
│   │   ├── deps.py                 # FastAPI 依赖注入 (get_db, get_current_user)
│   │   ├── models/
│   │   │   ├── __init__.py         # Base 导出
│   │   │   ├── device.py           # Device ORM
│   │   │   ├── camera.py           # Camera ORM
│   │   │   ├── recording.py        # Recording ORM
│   │   │   └── schedule.py         # Schedule ORM
│   │   ├── schemas/
│   │   │   ├── device.py           # Pydantic 请求/响应模型
│   │   │   ├── camera.py
│   │   │   ├── recording.py
│   │   │   └── schedule.py
│   │   ├── routers/
│   │   │   ├── devices.py          # /devices CRUD + scan
│   │   │   ├── cameras.py          # /cameras ONVIF + 录制控制
│   │   │   ├── recordings.py       # /recordings 列表 + 流式回放
│   │   │   ├── schedules.py        # /schedules CRUD
│   │   │   ├── ws.py               # /ws WebSocket
│   │   │   └── system.py           # /health, /auth/login
│   │   └── services/
│   │       ├── scanner.py          # ARP + nmap 扫描
│   │       ├── onvif_client.py     # ONVIF 封装
│   │       ├── recorder.py         # FFmpeg 录制 + 进程监控
│   │       ├── nas_syncer.py       # 文件同步
│   │       ├── scheduler_service.py # APScheduler 初始化和任务注册
│   │       └── ws_manager.py       # WebSocket 连接管理 (从 router 抽出)
│   ├── alembic/                    # 数据库迁移 (可选, 初期可用 create_all)
│   ├── .env.example
│   ├── requirements.txt
│   ├── Dockerfile
│   └── tests/
│       ├── test_scanner.py
│       ├── test_recorder.py
│       └── test_api.py
├── frontend/
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── router/index.js
│   │   ├── api/
│   │   │   ├── index.js            # Axios 实例 + 拦截器
│   │   │   ├── devices.js          # 设备相关 API 调用
│   │   │   ├── cameras.js
│   │   │   └── recordings.js
│   │   ├── composables/
│   │   │   └── useWebSocket.js     # WebSocket 重连封装
│   │   ├── stores/
│   │   │   ├── devices.js          # Pinia - 设备状态
│   │   │   ├── cameras.js          # Pinia - 摄像头状态
│   │   │   ├── auth.js             # Pinia - 认证状态
│   │   │   └── notifications.js    # Pinia - WebSocket 事件分发
│   │   ├── views/
│   │   │   ├── LoginView.vue       # 登录页
│   │   │   ├── DevicesView.vue     # 设备列表页
│   │   │   ├── CameraView.vue      # 摄像头管理页
│   │   │   ├── RecordingsView.vue  # 录像库
│   │   │   ├── ScheduleView.vue    # 录制计划
│   │   │   └── SettingsView.vue    # 系统配置
│   │   └── components/
│   │       ├── DeviceCard.vue
│   │       ├── CameraPlayer.vue
│   │       └── ScanProgress.vue
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
└── .gitignore
```

### 4.1 配置文件 (.env.example)

```env
# ─── 网络 ───
NETWORK_RANGE=192.168.1.0/24
SCAN_INTERVAL_SECONDS=60

# ─── 摄像头 (TP-Link IPC682F-A4) ───
# 支持多摄像头时在 Web 界面逐个添加，以下为初始默认
CAMERA_ONVIF_USER=admin
CAMERA_ONVIF_PASSWORD=your_camera_password

# ─── 绿联 NAS ───
NAS_MODE=mount                   # mount (Docker挂载, 推荐) 或 smb (网络推送)
NAS_MOUNT_PATH=/nas/cameras      # mount 模式: 容器内挂载路径
NAS_SMB_HOST=192.168.1.xxx       # smb 模式: NAS IP
NAS_SMB_SHARE=Backup             # smb 模式: 共享文件夹名
NAS_SMB_USER=nas_username         # smb 模式: 用户名
NAS_SMB_PASSWORD=nas_password     # smb 模式: 密码

# ─── 录制 ───
RECORDING_TEMP_DIR=/tmp/recordings
RECORDING_SEGMENT_SECONDS=1800   # 每段录制时长, 默认30分钟
RECORDING_RETENTION_DAYS=30      # 录像保留天数, 超期自动清理

# ─── 应用 ───
JWT_SECRET_KEY=change_me_to_a_random_string
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_me          # 首次启动后建议通过 Web 界面修改
LOG_LEVEL=INFO
DEBUG=false
```

---

## 5. 数据库设计

### 5.1 ER 关系

```
devices 1──1 cameras (device_type=camera 时)
cameras 1──N recordings
cameras 1──N schedules
```

### 5.2 表结构

**devices 表**

| 字段 | 类型 | 约束 | 说明 |
|:---|:---|:---|:---|
| id | INTEGER | PK, AUTOINCREMENT | |
| mac | TEXT | UNIQUE, NOT NULL, INDEX | MAC 地址，设备唯一标识 |
| ip | TEXT | | 最近一次扫描的 IP |
| vendor | TEXT | | 厂商（来自 OUI 库） |
| device_type | TEXT | DEFAULT 'unknown' | camera / computer / phone / iot / unknown |
| alias | TEXT | | 用户自定义名称 |
| is_online | BOOLEAN | DEFAULT FALSE | 当前在线状态 |
| last_seen | DATETIME | | 最后在线时间 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 首次发现时间 |
| updated_at | DATETIME | | 最后更新时间 |
| notes | TEXT | | 备注 |

**cameras 表**

| 字段 | 类型 | 约束 | 说明 |
|:---|:---|:---|:---|
| id | INTEGER | PK | |
| device_mac | TEXT | FK→devices.mac, UNIQUE | 一对一关联 |
| onvif_host | TEXT | NOT NULL | ONVIF 地址（通常等于设备 IP） |
| onvif_port | INTEGER | DEFAULT 2020 | ONVIF 端口 |
| onvif_user | TEXT | | ONVIF 认证用户名 |
| onvif_password | TEXT | | ONVIF 认证密码（AES 加密存储） |
| rtsp_port | INTEGER | DEFAULT 554 | RTSP 端口 |
| stream_profile | TEXT | DEFAULT 'mainStream' | 码流: mainStream / subStream |
| is_recording | BOOLEAN | DEFAULT FALSE | 当前是否正在录制 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | |

> **密码加密**：使用 `cryptography.fernet` 对称加密，密钥为 `JWT_SECRET_KEY` 派生。读取时解密，仅在后端内存中使用明文。

**recordings 表**

| 字段 | 类型 | 约束 | 说明 |
|:---|:---|:---|:---|
| id | INTEGER | PK | |
| camera_mac | TEXT | FK→cameras.device_mac, INDEX | 来源摄像头 |
| file_path | TEXT | NOT NULL | NAS 上的相对路径 |
| file_size | INTEGER | | 字节数 |
| duration | INTEGER | | 实际录制时长（秒） |
| started_at | DATETIME | NOT NULL, INDEX | 录制开始时间 |
| ended_at | DATETIME | | 录制结束时间 |
| status | TEXT | DEFAULT 'recording' | recording / completed / synced / failed |
| error_msg | TEXT | | 失败时的错误信息 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | |

> `status` 取代 v2 的 `synced_to_nas` 布尔值，提供更完整的生命周期追踪。

**schedules 表**

| 字段 | 类型 | 约束 | 说明 |
|:---|:---|:---|:---|
| id | INTEGER | PK | |
| camera_mac | TEXT | FK→cameras.device_mac | 目标摄像头 |
| name | TEXT | | 计划名称（如"夜间录制"） |
| cron_expr | TEXT | NOT NULL | cron 表达式 |
| segment_duration | INTEGER | DEFAULT 1800 | 每段时长（秒） |
| enabled | BOOLEAN | DEFAULT TRUE | 是否启用 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | |
| updated_at | DATETIME | | |

---

## 6. 认证设计

家庭局域网环境下采用轻量 JWT 方案，防止同网段其他设备未授权访问。

### 6.1 流程

```
1. 用户访问前端 → 无 token → 重定向到 /login
2. POST /api/v1/auth/login { username, password }
   → 校验通过 → 返回 { access_token, token_type: "bearer" }
   → 校验失败 → 401
3. 前端将 token 存入 localStorage，Axios 拦截器自动附加 Authorization header
4. 后端中间件验证 token → 有效则放行，无效则 401
5. WebSocket 连接时通过 query param 传递 token: ws://host/ws?token=xxx
```

### 6.2 实现要点

- **初始账户**：首次启动从 `.env` 的 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 创建。
- **Token 有效期**：24 小时（家庭场景不需要频繁重新登录）。
- **免认证端点**：`POST /auth/login`、`GET /health`。
- **密码存储**：bcrypt 哈希（通过 passlib），即使 SQLite 文件泄露也无法还原。

```python
# auth.py 核心逻辑
from jose import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(username: str, secret: str, expires_hours: int = 24) -> str:
    expire = datetime.utcnow() + timedelta(hours=expires_hours)
    return jwt.encode({"sub": username, "exp": expire}, secret, algorithm="HS256")

def verify_token(token: str, secret: str) -> str | None:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload.get("sub")
    except jwt.JWTError:
        return None
```

---

## 7. API 接口设计

基础路径：`http://<host>:8000/api/v1`

所有接口（除 `/auth/login` 和 `/health`）需携带 `Authorization: Bearer <token>`。

### 7.1 系统 `/`

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| GET | `/health` | 健康检查（数据库连通、FFmpeg 可用、NAS 可写） |
| POST | `/auth/login` | 登录，返回 JWT |

**GET /health 响应：**
```json
{
  "status": "healthy",
  "checks": {
    "database": true,
    "ffmpeg": true,
    "nas_writable": true,
    "cameras_reachable": { "total": 1, "online": 1 }
  },
  "uptime_seconds": 86400,
  "version": "1.0.0"
}
```

### 7.2 设备 `/devices`

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| GET | `/devices?page=1&page_size=20&type=camera&online=true` | 设备列表（分页 + 过滤） |
| POST | `/devices/scan` | 触发扫描，返回 `{ task_id }`，结果通过 WebSocket 推送 |
| GET | `/devices/{mac}` | 单个设备详情 |
| PATCH | `/devices/{mac}` | 更新别名、类型、备注 |
| DELETE | `/devices/{mac}` | 删除设备记录 |

**分页响应格式（所有列表接口统一）：**
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "pages": 3
}
```

### 7.3 摄像头 `/cameras`

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| GET | `/cameras` | 所有摄像头列表 |
| POST | `/cameras` | 添加摄像头（关联 device_mac，填写 ONVIF 凭据） |
| GET | `/cameras/{mac}` | 摄像头详情（含 ONVIF 设备信息） |
| PUT | `/cameras/{mac}` | 更新摄像头配置 |
| DELETE | `/cameras/{mac}` | 删除摄像头 |
| POST | `/cameras/{mac}/probe` | ONVIF 探测（返回设备信息、可用码流列表） |
| GET | `/cameras/{mac}/snapshot` | 实时截图（后端代理，不暴露 RTSP 凭据） |
| POST | `/cameras/{mac}/record/start` | 手动开始录制 |
| POST | `/cameras/{mac}/record/stop` | 手动停止录制 |

> 移除了 v2 的 `GET /cameras/{mac}/rtsp-url`，RTSP 地址含凭据，不应向前端暴露。前端通过后端代理获取截图和视频流。

### 7.4 录像 `/recordings`

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| GET | `/recordings?camera_mac=xx&date=2026-04-24&page=1&page_size=20` | 录像列表 |
| GET | `/recordings/{id}` | 录像详情（元数据） |
| GET | `/recordings/{id}/stream` | 视频流（支持 Range 请求，用于播放） |
| GET | `/recordings/{id}/download` | 下载原始文件 |
| DELETE | `/recordings/{id}` | 删除录像（同时删 NAS 文件） |

### 7.5 计划任务 `/schedules`

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| GET | `/schedules` | 所有录制计划 |
| POST | `/schedules` | 创建新计划 |
| GET | `/schedules/{id}` | 计划详情 |
| PATCH | `/schedules/{id}` | 修改计划（含 enable/disable） |
| DELETE | `/schedules/{id}` | 删除计划 |

### 7.6 WebSocket `/ws`

```
ws://<host>:8000/ws?token=<jwt_token>
```

**事件格式：**
```json
{
  "event": "device_status_changed",
  "timestamp": "2026-04-24T11:00:05",
  "data": { ... }
}
```

**事件类型：**

| 事件 | 触发时机 | data 内容 |
|:---|:---|:---|
| `device_online` | 设备上线 | `{ mac, ip, alias }` |
| `device_offline` | 设备离线 | `{ mac, alias, last_seen }` |
| `scan_started` | 扫描开始 | `{}` |
| `scan_completed` | 扫描完成 | `{ found: 12, new: 1, offline: 2 }` |
| `recording_started` | 录制开始 | `{ camera_mac, recording_id }` |
| `recording_completed` | 录制完成 | `{ camera_mac, recording_id, file_path, duration }` |
| `recording_failed` | 录制异常 | `{ camera_mac, error }` |
| `nas_sync_completed` | NAS 同步完成 | `{ recording_id, file_path }` |

### 7.7 统一错误响应

```json
{
  "error": {
    "code": "CAMERA_OFFLINE",
    "message": "摄像头 50:C7:BF:xx:xx:xx 当前离线，无法开始录制",
    "detail": null
  }
}
```

**错误码清单：**

| HTTP | code | 说明 |
|:---|:---|:---|
| 400 | `INVALID_CRON` | cron 表达式格式错误 |
| 401 | `UNAUTHORIZED` | 未登录或 token 过期 |
| 404 | `DEVICE_NOT_FOUND` | 设备不存在 |
| 404 | `CAMERA_NOT_FOUND` | 摄像头未配置 |
| 409 | `ALREADY_RECORDING` | 该摄像头已在录制中 |
| 409 | `NOT_RECORDING` | 该摄像头未在录制，无法停止 |
| 422 | `CAMERA_OFFLINE` | 摄像头离线 |
| 500 | `FFMPEG_ERROR` | FFmpeg 进程启动失败 |
| 500 | `NAS_WRITE_ERROR` | NAS 写入失败（磁盘满、权限等） |
| 500 | `ONVIF_ERROR` | ONVIF 通信异常 |

---

## 8. 关键模块实现

### 8.1 设备扫描 (scanner.py)

```python
import asyncio
from scapy.all import ARP, Ether, srp
import nmap
from mac_vendor_lookup import AsyncMacLookup
from loguru import logger

class Scanner:
    def __init__(self, network: str):
        self.network = network
        self._mac_lookup = AsyncMacLookup()

    async def arp_scan(self) -> list[dict]:
        """ARP 扫描，约 3-5 秒完成整个 /24 子网"""
        logger.info(f"开始 ARP 扫描: {self.network}")
        loop = asyncio.get_event_loop()
        # scapy 是同步阻塞库，必须放到线程池
        result = await loop.run_in_executor(None, self._arp_scan_sync)
        logger.info(f"ARP 扫描完成，发现 {len(result)} 台设备")
        return result

    def _arp_scan_sync(self) -> list[dict]:
        pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=self.network)
        answered, _ = srp(pkt, timeout=3, verbose=0)
        return [
            {"ip": rcv.psrc, "mac": rcv.hwsrc.upper()}
            for _, rcv in answered
        ]

    async def lookup_vendor(self, mac: str) -> str:
        try:
            return await self._mac_lookup.lookup(mac)
        except Exception:
            return "Unknown"

    async def probe_ports(self, ip: str) -> list[int]:
        """nmap 端口探测，同步库需要线程池包装"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._probe_ports_sync, ip)

    def _probe_ports_sync(self, ip: str) -> list[int]:
        nm = nmap.PortScanner()
        nm.scan(ip, "80,443,554,2020,8080,8443", arguments="-T4 --open")
        ports = []
        if ip in nm.all_hosts():
            for proto in nm[ip].all_protocols():
                ports.extend(nm[ip][proto].keys())
        return ports

    @staticmethod
    def guess_device_type(vendor: str, open_ports: list[int]) -> str:
        if 554 in open_ports or 2020 in open_ports:
            return "camera"
        v = vendor.lower()
        if any(kw in v for kw in ("apple", "samsung", "xiaomi", "huawei", "oppo", "vivo")):
            return "phone"
        if any(kw in v for kw in ("intel", "realtek", "dell", "lenovo", "hp ", "asus")):
            return "computer"
        return "unknown"
```

### 8.2 ONVIF 摄像头接入 (onvif_client.py)

```python
import asyncio
from onvif import ONVIFCamera
from loguru import logger

class OnvifClient:
    """
    onvif-zeep 是同步库，所有方法通过 run_in_executor 包装为 async。
    """

    def __init__(self, host: str, port: int, user: str, password: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self._camera = None

    def _get_camera(self) -> ONVIFCamera:
        if self._camera is None:
            self._camera = ONVIFCamera(self.host, self.port, self.user, self.password)
        return self._camera

    async def get_device_info(self) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_device_info_sync)

    def _get_device_info_sync(self) -> dict:
        cam = self._get_camera()
        svc = cam.create_devicemgmt_service()
        info = svc.GetDeviceInformation()
        return {
            "manufacturer": info.Manufacturer,
            "model": info.Model,
            "firmware": info.FirmwareVersion,
            "serial": info.SerialNumber,
        }

    async def get_stream_uri(self, profile_index: int = 0) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_stream_uri_sync, profile_index)

    def _get_stream_uri_sync(self, profile_index: int) -> str:
        cam = self._get_camera()
        media = cam.create_media_service()
        profiles = media.GetProfiles()
        if profile_index >= len(profiles):
            profile_index = 0
        token = profiles[profile_index].token
        uri = media.GetStreamUri({
            "StreamSetup": {
                "Stream": "RTP-Unicast",
                "Transport": {"Protocol": "RTSP"},
            },
            "ProfileToken": token,
        })
        return uri.Uri

    async def get_snapshot_uri(self) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_snapshot_uri_sync)

    def _get_snapshot_uri_sync(self) -> str:
        cam = self._get_camera()
        media = cam.create_media_service()
        profiles = media.GetProfiles()
        token = profiles[0].token
        uri = media.GetSnapshotUri({"ProfileToken": token})
        return uri.Uri

    async def get_profiles(self) -> list[dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_profiles_sync)

    def _get_profiles_sync(self) -> list[dict]:
        cam = self._get_camera()
        media = cam.create_media_service()
        profiles = media.GetProfiles()
        return [
            {
                "index": i,
                "name": p.Name,
                "token": p.token,
                "encoding": getattr(p, 'VideoEncoderConfiguration', {}).get('Encoding', 'unknown') if hasattr(p, 'VideoEncoderConfiguration') else "unknown",
            }
            for i, p in enumerate(profiles)
        ]

    async def is_reachable(self) -> bool:
        try:
            await self.get_device_info()
            return True
        except Exception as e:
            logger.debug(f"ONVIF 不可达 {self.host}:{self.port}: {e}")
            return False
```

> **TP-Link IPC682F-A4 注意事项：**
> 1. ONVIF 端口通常为 **2020**（非标准 80），需在摄像头 Web 管理界面开启。
> 2. 该型号可能需要在 TP-Link 管理页面 → 高级设置 → 网络 → ONVIF 中手动启用。
> 3. RTSP URL 格式通常为 `rtsp://user:pass@ip:554/stream1`（主码流）或 `/stream2`（子码流），但建议通过 ONVIF `GetStreamUri` 自动获取，避免硬编码。

### 8.3 FFmpeg 录制 + 进程监控 (recorder.py)

```python
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from loguru import logger

@dataclass
class RecordingTask:
    camera_mac: str
    process: subprocess.Popen
    output_path: Path
    started_at: datetime
    segment_seconds: int
    rtsp_url: str  # 用于重试

class Recorder:
    def __init__(self, temp_dir: str):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.active: dict[str, RecordingTask] = {}
        self._monitor_task: asyncio.Task | None = None

    async def start_monitor(self):
        """启动后台监控协程，在 FastAPI lifespan 中调用"""
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_monitor(self):
        if self._monitor_task:
            self._monitor_task.cancel()

    async def start_recording(
        self, camera_mac: str, rtsp_url: str, segment_seconds: int = 1800
    ) -> str:
        if camera_mac in self.active:
            raise RuntimeError(f"摄像头 {camera_mac} 已在录制中")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_mac = camera_mac.replace(":", "")
        output_path = self.temp_dir / f"{safe_mac}_{ts}.mp4"

        cmd = [
            "ffmpeg", "-y",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-c", "copy",
            "-t", str(segment_seconds),
            "-movflags", "+faststart",
            str(output_path),
        ]

        logger.info(f"启动录制: {camera_mac} → {output_path}")
        loop = asyncio.get_event_loop()
        proc = await loop.run_in_executor(
            None,
            lambda: subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            ),
        )

        self.active[camera_mac] = RecordingTask(
            camera_mac=camera_mac,
            process=proc,
            output_path=output_path,
            started_at=datetime.now(),
            segment_seconds=segment_seconds,
            rtsp_url=rtsp_url,
        )
        return str(output_path)

    async def stop_recording(self, camera_mac: str) -> Path | None:
        task = self.active.pop(camera_mac, None)
        if not task:
            return None

        logger.info(f"停止录制: {camera_mac}")
        # 发送 SIGINT 让 FFmpeg 正常写入文件尾部
        task.process.send_signal(2)  # SIGINT
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, task.process.wait, 10)

        if task.process.poll() is None:
            task.process.kill()

        if task.output_path.exists() and task.output_path.stat().st_size > 0:
            return task.output_path
        return None

    async def _monitor_loop(self):
        """每 10 秒检查所有活跃录制进程的状态"""
        while True:
            await asyncio.sleep(10)
            finished = []
            for mac, task in self.active.items():
                retcode = task.process.poll()
                if retcode is not None:
                    finished.append((mac, retcode, task))

            for mac, retcode, task in finished:
                self.active.pop(mac, None)
                if retcode == 0:
                    logger.info(f"录制正常完成: {mac}, 文件: {task.output_path}")
                    # 触发回调: 同步到 NAS, 写数据库等
                    # 由 scheduler_service 注册的回调处理
                    await self._on_recording_complete(task)
                else:
                    stderr = task.process.stderr.read().decode(errors="replace")[-500:]
                    logger.error(f"录制异常退出: {mac}, code={retcode}, stderr: {stderr}")
                    await self._on_recording_failed(task, retcode, stderr)

    async def _on_recording_complete(self, task: RecordingTask):
        """录制完成回调 — 由外部通过依赖注入设置实际处理逻辑"""
        pass  # 实际实现中通过事件总线或回调函数注入

    async def _on_recording_failed(self, task: RecordingTask, code: int, stderr: str):
        """录制失败回调"""
        pass
```

### 8.4 NAS 同步 (nas_syncer.py)

```python
import shutil
from pathlib import Path
from datetime import datetime
from loguru import logger

class NasSyncer:
    def __init__(self, mode: str, mount_path: str = "",
                 smb_host: str = "", smb_share: str = "",
                 smb_user: str = "", smb_password: str = ""):
        self.mode = mode  # "mount" 或 "smb"
        self.mount_path = Path(mount_path) if mount_path else None
        self.smb_config = {
            "host": smb_host, "share": smb_share,
            "user": smb_user, "password": smb_password,
        }

    def sync_file(self, src: Path, camera_mac: str) -> Path:
        """
        将临时录制文件同步到 NAS。
        目标路径: <base>/<camera_mac>/<YYYY-MM-DD>/<filename>
        """
        date_dir = datetime.now().strftime("%Y-%m-%d")
        safe_mac = camera_mac.replace(":", "")
        relative = f"{safe_mac}/{date_dir}/{src.name}"

        if self.mode == "mount":
            return self._sync_via_mount(src, relative)
        elif self.mode == "smb":
            return self._sync_via_smb(src, relative)
        else:
            raise ValueError(f"未知 NAS_MODE: {self.mode}")

    def _sync_via_mount(self, src: Path, relative: str) -> Path:
        dest = self.mount_path / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"NAS同步(mount): {src} → {dest}")
        shutil.move(str(src), str(dest))
        return dest

    def _sync_via_smb(self, src: Path, remote_path: str) -> Path:
        from smbclient import register_session, open_file
        register_session(
            self.smb_config["host"],
            username=self.smb_config["user"],
            password=self.smb_config["password"],
        )
        share = self.smb_config["share"]
        full_remote = f"\\\\{self.smb_config['host']}\\{share}\\{remote_path}"

        logger.info(f"NAS同步(SMB): {src} → {full_remote}")
        with open(src, "rb") as local_f:
            with open_file(full_remote, mode="wb") as remote_f:
                shutil.copyfileobj(local_f, remote_f, length=1024 * 1024)

        src.unlink()  # 同步成功后删除临时文件
        return Path(full_remote)

    def check_writable(self) -> bool:
        """健康检查: NAS 是否可写"""
        try:
            if self.mode == "mount":
                test_file = self.mount_path / ".health_check"
                test_file.write_text("ok")
                test_file.unlink()
                return True
            else:
                # SMB 模式: 尝试建立连接
                from smbclient import register_session
                register_session(
                    self.smb_config["host"],
                    username=self.smb_config["user"],
                    password=self.smb_config["password"],
                )
                return True
        except Exception as e:
            logger.error(f"NAS 健康检查失败: {e}")
            return False
```

> **v2→v3 变更**：使用 `smbclient`（`smbprotocol` 的高级封装）替代直接操作低级 SMB 对象，代码更简洁。`NAS_MODE` 环境变量显式控制模式，不再猜测。

### 8.5 WebSocket 管理 (ws_manager.py)

```python
import asyncio
import json
from datetime import datetime
from fastapi import WebSocket
from loguru import logger

class WebSocketManager:
    def __init__(self):
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)
        logger.info(f"WebSocket 连接: {ws.client}, 当前连接数: {len(self._connections)}")

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self._connections.discard(ws)
        logger.info(f"WebSocket 断开: {ws.client}, 当前连接数: {len(self._connections)}")

    async def broadcast(self, event: str, data: dict):
        message = json.dumps({
            "event": event,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }, ensure_ascii=False)

        # 拷贝快照避免遍历时修改
        async with self._lock:
            connections = self._connections.copy()

        stale = []
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                stale.append(ws)

        # 清理断开的连接
        if stale:
            async with self._lock:
                for ws in stale:
                    self._connections.discard(ws)

ws_manager = WebSocketManager()
```

### 8.6 视频流式回放 (recordings router 片段)

```python
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pathlib import Path

router = APIRouter(prefix="/recordings")

@router.get("/{recording_id}/stream")
async def stream_recording(recording_id: int, request: Request):
    """支持 HTTP Range 请求的 MP4 流式回放"""
    # 从数据库查询 file_path (省略 DB 查询代码)
    file_path = Path(...)  # recording.file_path

    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")

    if range_header:
        # 解析 Range: bytes=start-end
        range_spec = range_header.replace("bytes=", "")
        parts = range_spec.split("-")
        start = int(parts[0])
        end = int(parts[1]) if parts[1] else file_size - 1
        content_length = end - start + 1

        def iter_file():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk = f.read(min(8192, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        return StreamingResponse(
            iter_file(),
            status_code=206,
            media_type="video/mp4",
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(content_length),
                "Accept-Ranges": "bytes",
            },
        )
    else:
        def iter_full():
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk

        return StreamingResponse(
            iter_full(),
            media_type="video/mp4",
            headers={
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
            },
        )
```

---

## 9. 前端设计

### 9.1 页面路由

```javascript
// router/index.js
const routes = [
  { path: '/login', component: LoginView, meta: { public: true } },
  { path: '/', redirect: '/devices' },
  { path: '/devices', component: DevicesView },
  { path: '/cameras', component: CameraView },
  { path: '/recordings', component: RecordingsView },
  { path: '/schedule', component: ScheduleView },
  { path: '/settings', component: SettingsView },
]

// 路由守卫: 未登录重定向到 /login
router.beforeEach((to) => {
  if (!to.meta.public && !localStorage.getItem('token')) {
    return '/login'
  }
})
```

### 9.2 WebSocket 重连封装

```javascript
// composables/useWebSocket.js
import { ref, onUnmounted } from 'vue'

export function useWebSocket(url, { onMessage, maxRetries = Infinity } = {}) {
  const connected = ref(false)
  let ws = null
  let retries = 0
  let retryTimer = null

  function connect() {
    const token = localStorage.getItem('token')
    ws = new WebSocket(`${url}?token=${token}`)

    ws.onopen = () => {
      connected.value = true
      retries = 0
    }

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      onMessage?.(msg)
    }

    ws.onclose = () => {
      connected.value = false
      if (retries < maxRetries) {
        // 指数退避: 1s, 2s, 4s, 8s, 最大 30s
        const delay = Math.min(1000 * Math.pow(2, retries), 30000)
        retryTimer = setTimeout(() => {
          retries++
          connect()
        }, delay)
      }
    }

    ws.onerror = () => ws.close()
  }

  function disconnect() {
    clearTimeout(retryTimer)
    ws?.close()
  }

  connect()
  onUnmounted(disconnect)

  return { connected, disconnect }
}
```

### 9.3 Axios 拦截器

```javascript
// api/index.js
import axios from 'axios'
import router from '@/router'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      router.push('/login')
    }
    return Promise.reject(err)
  }
)

export default api
```

### 9.4 设备列表页 UI 草图

```
┌──────────────────────────────────────────────────────────────┐
│  🏠 智能家居管理                [WS ● 已连接]  [admin ▼]     │
├──────────────────────────────────────────────────────────────┤
│  设备  │ 摄像头  │ 录像库  │ 录制计划  │ 设置                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  设备总览   在线 9 / 总计 12          [⟳ 扫描网络] (加载中..)│
│                                                              │
│  筛选: [全部类型 ▼] [全部状态 ▼]  搜索: [___________]       │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ ● 客厅摄像头         192.168.1.108    TP-LINK          │  │
│  │   50:C7:BF:xx:xx     camera           在线 2分钟前     │  │
│  │                              [编辑] [ONVIF探测] [录制]  │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ ● 小明的 iPhone      192.168.1.55     Apple             │  │
│  │   F8:4D:89:xx:xx     phone            在线 1分钟前     │  │
│  │                                               [编辑]    │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ ○ 未知设备           192.168.1.77     Xiaomi            │  │
│  │   B4:A9:FC:xx:xx     unknown          离线 3小时前     │  │
│  │                                    [编辑] [标记类型]    │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ◂ 1 / 1 ▸                                                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 10. 部署方案

### 10.1 推荐方案：绿联 NAS Docker 部署

**docker-compose.yml：**
```yaml
services:
  smart-home:
    build:
      context: .
      dockerfile: backend/Dockerfile
    restart: unless-stopped
    network_mode: host
    volumes:
      - /volume1/Backup/cameras:/nas/cameras
      - /tmp/smart-home-recordings:/tmp/recordings
      - ./data:/app/data                  # SQLite + 日志持久化
    env_file:
      - .env
    cap_add:
      - NET_ADMIN                          # ARP 扫描需要
      - NET_RAW                            # scapy 原始套接字需要
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 60s
      timeout: 5s
      retries: 3
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

**backend/Dockerfile：**
```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg nmap libpcap-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY frontend/dist ./static

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

> **前端打包后作为静态文件由后端 FastAPI 直接服务**（`app.mount("/", StaticFiles(directory="static"))`），无需单独的 nginx 容器。简化部署、减少资源占用。

### 10.2 降级方案：独立主机部署

如果不想在 NAS 上运行 Docker：
- 后端部署在树莓派或局域网 PC。
- `.env` 中设置 `NAS_MODE=smb`，配置 SMB 凭据。
- NAS 端需开启 SMB 共享并创建专用账户（只授予 Backup 目录读写权限）。
- ARP 扫描需要 root 权限或 `setcap cap_net_raw+ep` 赋权。

### 10.3 前端构建集成

```bash
# 构建前端
cd frontend && npm run build
# 产物在 frontend/dist/，Dockerfile 中 COPY 到后端 static 目录
```

Vite 配置 API 代理（开发环境）：
```javascript
// vite.config.js
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    }
  }
})
```

---

## 11. 安全注意事项

| 维度 | 措施 |
|:---|:---|
| 凭据存储 | 所有密码走 `.env`，`.gitignore` 中排除。摄像头密码在数据库中 AES 加密 |
| 认证 | JWT + bcrypt，未登录无法访问任何 API（除 health 和 login） |
| RTSP 保护 | RTSP URL 不暴露给前端，截图和视频流通过后端代理 |
| 网络隔离 | 仅监听局域网。外网访问通过 Tailscale/WireGuard VPN，**不直接映射端口** |
| NAS 权限 | 专用账户，仅授予 Backup 目录读写权限 |
| Docker 权限 | 仅授予 `NET_ADMIN` 和 `NET_RAW`，不使用 `--privileged` |
| 扫描限制 | ARP 扫描间隔不低于 30s，防止对局域网造成广播风暴 |
| 日志脱敏 | 日志中不记录密码、token 明文 |

---

## 12. 开发阶段规划

> 总预估：**3 周**（含联调、硬件适配、基本测试）

### Phase 1：项目骨架 + 设备发现（第 1 周前半）

- [ ] FastAPI 项目初始化 + SQLAlchemy + SQLite
- [ ] Pydantic Settings + .env 配置
- [ ] JWT 认证中间件 + 登录接口
- [ ] ARP 扫描服务 + MAC OUI 查厂商
- [ ] 设备 CRUD API
- [ ] Vue 前端脚手架 + 登录页 + 设备列表页
- [ ] **验证点**：浏览器访问 → 登录 → 看到扫描出的设备列表

### Phase 2：摄像头接入（第 1 周后半 ~ 第 2 周前半）

- [ ] ONVIF 客户端封装 + 探测接口
- [ ] **硬件验证**：确认 TP-Link ONVIF 端口和认证方式
- [ ] FFmpeg 录制服务 + 手动录制 API
- [ ] **硬件验证**：`ffmpeg -i rtsp://... -c copy -t 60 test.mp4` 生成有效文件
- [ ] 前端摄像头管理页（ONVIF 信息展示、截图预览、录制按钮）
- [ ] **验证点**：前端点击录制 → 后端 FFmpeg 产出 MP4 → 前端可播放

> **风险提示**：TP-Link 的 ONVIF 实现可能不完全标准，预留 1-2 天排查兼容性问题。常见坑：端口非 80、需要手动启用、认证方式不兼容。备选方案：跳过 ONVIF 自动发现，直接在 Web 界面手动配置 RTSP 地址。

### Phase 3：自动录制 + NAS 同步（第 2 周后半）

- [ ] APScheduler 集成 + 计划任务 CRUD API
- [ ] RecordingMonitor 进程监控
- [ ] NAS 同步服务（mount 模式）
- [ ] 录像元数据写入数据库
- [ ] 视频流式回放 API (Range 请求)
- [ ] 前端录像库页面（列表 + Video.js 播放）
- [ ] 前端计划任务管理页
- [ ] **验证点**：创建定时计划 → 自动录制 → 文件出现在 NAS 目录 → 前端可回放

### Phase 4：实时推送 + 部署收尾（第 3 周）

- [ ] WebSocket 推送 + 前端重连
- [ ] Docker 镜像构建 + docker-compose
- [ ] NAS 部署测试（`network_mode: host` + 卷挂载）
- [ ] 错误处理完善（摄像头离线、NAS 满盘、FFmpeg 崩溃）
- [ ] loguru 日志配置 + 文件轮转
- [ ] 录像自动清理（过期删除）
- [ ] 基础功能回归测试
- [ ] **验证点**：NAS Docker 中完整运行 24 小时无异常

---

## 13. 待验证清单（开发前必做）

按优先级排列：

1. [ ] **RTSP 可用性**：VLC 输入 `rtsp://admin:password@摄像头IP:554/stream1` 能看到画面
2. [ ] **FFmpeg 录制**：`ffmpeg -rtsp_transport tcp -i "rtsp://..." -c copy -t 60 test.mp4` 生成有效 MP4
3. [ ] **ONVIF 端口**：在 TP-Link 管理界面确认 ONVIF 端口号（通常 2020）并启用
4. [ ] **ONVIF 连通**：`python -c "from onvif import ONVIFCamera; c = ONVIFCamera('IP', 2020, 'user', 'pass'); print(c.devicemgmt.GetDeviceInformation())"` 返回设备信息
5. [ ] **NAS Docker host 网络**：在绿联 NAS Docker 中运行 `network_mode: host` 的容器，执行 ARP 扫描能发现局域网设备
6. [ ] **NAS 挂载可写**：Docker 容器内 `touch /nas/cameras/test && rm /nas/cameras/test` 成功
7. [ ] **nmap 权限**：Docker 容器内 `nmap -sS 192.168.1.1 -p 554` 正常执行

---

## 14. 依赖清单 (requirements.txt)

```
# Web 框架
fastapi>=0.111.0
uvicorn[standard]>=0.30.0

# 数据库
sqlalchemy[asyncio]>=2.0.0
aiosqlite>=0.20.0

# 配置
python-dotenv>=1.0.0
pydantic-settings>=2.0.0

# 认证
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4

# 设备扫描
python-nmap>=0.7.1
scapy>=2.5.0
mac-vendor-lookup>=0.1.12

# 摄像头
onvif-zeep>=0.2.12

# NAS (SMB 降级方案)
smbprotocol>=1.13.0

# 任务调度
apscheduler>=3.10.0,<4.0.0

# 加密
cryptography>=42.0.0

# 日志
loguru>=0.7.0

# 工具
python-multipart>=0.0.9
httpx>=0.27.0
```

> 移除了 v2 的 `ffmpeg-python`（不使用）和 `websockets`（FastAPI 内置 WebSocket 支持）。新增 `python-jose`、`passlib`、`cryptography`、`loguru`、`httpx`。

---

## 15. 后续扩展方向（不在当前版本范围）

记录可能的演进方向，供后续版本参考，**当前版本不实现**：

- **多摄像头支持**：当前架构已预留（camera 表独立），但 UI 和调度需要适配
- **移动端推送**：摄像头离线时通过 Bark/Server酱 推送手机通知
- **AI 移动检测**：对录像片段做运动检测，标记有事件的时间段
- **存储管理仪表盘**：NAS 磁盘用量、录像增长趋势图
- **多用户权限**：角色区分（管理员/只读用户）

---

*本文档版本 v3，基于 v2 技术评审后优化。核心改进：修复 async/sync 阻塞问题、降级 APScheduler 到稳定版、补全 JWT 认证、增加 FFmpeg 进程监控、WebSocket 线程安全和前端重连、NAS 模式显式配置、API 分页和错误码体系、调整开发周期为 3 周。*
