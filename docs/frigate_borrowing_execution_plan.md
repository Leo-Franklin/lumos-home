# Frigate 借鉴项执行计划

## 背景

Lumos Home 当前定位不是 Frigate 的直接替代品。Frigate 是以本地 AI NVR 为核心的摄像头系统，重点在实时对象检测、事件录像、低延迟直播、Home Assistant/MQTT 集成和成熟的视频管线。

Lumos Home 更适合定位为智能家居管理与编排平台：设备发现、摄像头管理、NAS 录像、DLNA 投屏、家庭成员在线、自动化联动和 Windows 本地安装。摄像头模块需要借鉴 Frigate 的成熟工程经验，但不应短期复制完整 AI NVR。

## 总体原则

1. 先补视频基础设施，再做智能检测。
2. 先做可集成能力，再做自研替代能力。
3. 优先解决稳定性、资源占用、事件模型和生态接口。
4. 保留 Lumos Home 的差异化：家庭设备编排、NAS/DLNA、本地安装、中文家庭场景。
5. 对 Frigate 能做得很成熟的能力，优先集成而不是重写。

## 优先级总览

| 优先级 | 阶段 | 目标 | 是否建议短期做 |
| --- | --- | --- | --- |
| P0 | 视频管线稳定化 | 降低 RTSP/HLS/录制维护风险 | 是 |
| P0 | 事件模型重构 | 从“录像文件”升级为“事件 + 片段” | 是 |
| P1 | 保留策略与回放体验 | 提升 NVR 可用性 | 是 |
| P1 | MQTT / Frigate Bridge | 接入现成生态，避免重复造 AI NVR | 是 |
| P2 | 区域、遮罩、隐私能力 | 为后续检测和家庭场景铺路 | 中期 |
| P2 | 轻量运动检测 | 提供无 AI 硬件下的事件触发 | 中期 |
| P3 | 本地 AI 检测 | 作为可选能力，不作为近期主线 | 后期 |

## P0-1 视频管线稳定化

### 借鉴点

Frigate 将摄像头输入、restream、检测、录制、直播播放拆成独立管线，并通过 go2rtc 等组件降低摄像头连接数和直播延迟。

### 当前问题

- HLS 实时流、录制、健康检查分别直接访问 RTSP，容易对摄像头产生多连接压力。
- API 路由承担了较多 ffmpeg 进程生命周期管理。
- 多摄像头场景下，资源上限、重连策略、进程清理和日志诊断会变复杂。

### 执行任务

- [ ] 梳理当前所有 RTSP 使用点：录制、HLS、MJPEG、snapshot、ffprobe 健康检查。
- [ ] 抽象 `StreamManager` 服务，统一管理摄像头流状态、启动、停止、重启、健康信息。
- [ ] 将 HLS 进程管理从 `cameras.py` 路由中下沉到服务层。
- [ ] 为每路摄像头维护 stream runtime 状态：`idle`、`starting`、`running`、`stalled`、`failed`。
- [ ] 增加流进程资源限制：最大并发 HLS 数、最大录制数、启动超时、停止超时。
- [ ] 调研 go2rtc 集成方式：内置二进制、Docker sidecar、用户自装三种模式。
- [ ] 形成 `go2rtc` 适配层设计，但第一步不要强依赖 go2rtc。

### 验收标准

- HLS、录制、健康检查不再各自散落管理 ffmpeg 进程。
- 后端重启或前端关闭后不会遗留孤儿 ffmpeg 进程。
- 单摄像头同时预览和录制时，摄像头 RTSP 连接数可被观测并受控。
- 发生 RTSP 断流时，前端能看到明确状态，后端日志能定位原因。

## P0-2 事件模型重构

### 借鉴点

Frigate 的核心不是简单保存录像文件，而是围绕事件组织录像、快照、标签、时间线和回看入口。

### 当前问题

- 当前 `recordings` 更偏文件记录，缺少事件层。
- 手动录制、定时录制、成员触发录制、未来的运动检测/AI 检测没有统一事件模型。
- 后续做搜索、时间线、保留策略、通知时会受限。

### 执行任务

- [ ] 新增 `camera_events` 表，字段建议：
  - `id`
  - `camera_mac`
  - `event_type`
  - `source`
  - `started_at`
  - `ended_at`
  - `severity`
  - `status`
  - `summary`
  - `thumbnail_path`
  - `metadata_json`
- [ ] 将 `recordings` 改为可关联 `event_id`。
- [ ] 定义事件类型：
  - `manual_recording`
  - `scheduled_recording`
  - `presence_triggered`
  - `motion`
  - `external_frigate`
  - `system`
- [ ] 定义事件来源：
  - `lumos`
  - `frigate`
  - `user`
  - `scheduler`
  - `presence`
- [ ] 新增事件 API：
  - `GET /api/v1/camera-events`
  - `GET /api/v1/camera-events/{id}`
  - `PATCH /api/v1/camera-events/{id}`
  - `DELETE /api/v1/camera-events/{id}`
- [ ] 录制开始时创建事件，录制完成时补齐结束时间、片段、封面和状态。
- [ ] 前端新增事件时间线视图，录像列表逐步迁移为事件优先。

### 验收标准

- 手动录制、定时录制、成员触发录制都能生成统一事件。
- 一个事件可以关联多个录像分段。
- 前端可以按摄像头、日期、事件类型过滤。
- 后续接入 Frigate 事件时不需要重构基础数据模型。

## P1-1 保留策略与回放体验

### 借鉴点

Frigate 支持按检测类型、事件价值和时间配置保留策略，并提供较成熟的回看工作流。

### 当前问题

- 录像保留更多是全局按天清理。
- 用户很难区分重要录像和普通录像。
- 多段录像与事件回放体验需要进一步整理。

### 执行任务

- [ ] 设计保留策略模型 `retention_policies`。
- [ ] 支持按摄像头配置保留天数。
- [ ] 支持按事件类型配置保留天数。
- [ ] 增加收藏/锁定能力，锁定事件不被自动清理。
- [ ] 增加事件封面图生成：优先从录像第一帧截取。
- [ ] 前端回放页从“文件列表”增强为“事件时间线 + 分段播放”。
- [ ] 增加批量删除、批量锁定、按日期清理。

### 验收标准

- 用户可以配置不同摄像头的保留策略。
- 用户可以保留重要事件，自动清理不会误删锁定事件。
- 一个多段事件能在前端以单个事件呈现。
- 录像清理任务有日志、统计和失败重试。

## P1-2 MQTT 与 Frigate Bridge

### 借鉴点

Frigate 通过 MQTT 与 Home Assistant 和其他系统集成，这是它生态价值的重要部分。Lumos Home 应优先接入 Frigate，而不是立刻复制检测能力。

### 当前问题

- 本项目 WebSocket 主要服务前端，缺少标准外部事件总线。
- Frigate 已经能产生对象检测事件，本项目没有必要短期重做。
- Home Assistant 用户无法自然复用 Lumos Home 的状态。

### 执行任务

- [ ] 增加 MQTT 配置：
  - broker host
  - port
  - username
  - password
  - topic prefix
  - TLS 开关
- [ ] 新增 `MqttService`，负责发布 Lumos Home 内部事件。
- [ ] 发布基础事件：
  - 设备上线/离线
  - 摄像头上线/离线
  - 录制开始/完成/失败
  - 成员到家/离家
  - 未知设备发现
- [ ] 新增 `FrigateBridgeService`，订阅 Frigate MQTT 事件。
- [ ] 将 Frigate 事件映射到 `camera_events`：
  - person
  - car
  - package
  - animal
  - motion
  - custom label
- [ ] 前端设置页增加 Frigate Bridge 配置和连接测试。
- [ ] Dashboard 活动流展示 Frigate 外部事件。

### 验收标准

- Lumos Home 内部事件可以通过 MQTT 被外部系统消费。
- Frigate 的检测事件能进入 Lumos Home 事件时间线。
- 用户可以基于 Frigate 的 person/car 事件触发 Lumos Home 的 NAS/DLNA/通知联动。
- Frigate 不在线时，Lumos Home 原有轻量摄像头能力不受影响。

## P2-1 区域、遮罩与隐私配置

### 借鉴点

Frigate 的 mask/zone 编辑能力能减少误报，也能表达用户关心的区域。即使暂时不做 AI，这套配置也对运动检测、隐私保护和未来事件过滤有价值。

### 当前问题

- 摄像头只有基础配置和录制预设。
- 没有区域、遮罩、隐私屏蔽等结构化配置。
- 后续做运动检测和 AI 检测时缺少用户可配置边界。

### 执行任务

- [ ] 新增 `camera_zones` 表。
- [ ] 新增 `camera_masks` 表。
- [ ] 前端摄像头详情页增加区域编辑器。
- [ ] 支持在截图画面上绘制 polygon。
- [ ] 区域类型初步定义：
  - `interest`
  - `ignore`
  - `privacy`
- [ ] HLS/截图接口支持隐私遮罩渲染的技术调研。
- [ ] 为未来 motion/object detection 预留 zone filter 字段。

### 验收标准

- 用户可以为每个摄像头配置多个区域和遮罩。
- 配置可以导出/导入。
- 后续事件可以关联 zone 名称。
- 隐私区域不会在缩略图或事件封面中暴露。

## P2-2 轻量运动检测

### 借鉴点

Frigate 用低成本运动检测决定何时运行更重的对象检测。Lumos Home 可以先实现轻量 motion 事件，用于无 AI 硬件的家庭场景。

### 当前问题

- 录像触发主要来自手动、定时、成员状态。
- 摄像头画面变化不能形成事件。
- 没有检测前置能力，直接做 AI 会过重。

### 执行任务

- [ ] 设计 `MotionDetectorService`，作为可选后台服务。
- [ ] 使用低帧率抽帧，不直接处理主码流全帧。
- [ ] 支持每摄像头开启/关闭 motion detection。
- [ ] 支持灵敏度、最短事件时间、冷却时间。
- [ ] 接入 P2-1 的 ignore/privacy zones。
- [ ] motion 事件写入 `camera_events`。
- [ ] motion 事件可触发短录像。

### 验收标准

- 无 AI 硬件也能基于画面变化产生事件。
- 单路 motion 检测 CPU 占用可控。
- 用户可以通过区域/灵敏度减少误触发。
- motion 事件可以触发录制、通知和 NAS 同步。

## P3 本地 AI 检测

### 借鉴点

Frigate 支持多种检测器和硬件加速，包括 Edge TPU、OpenVINO、ONNX、TensorRT、Hailo、Rockchip 等。Lumos Home 不应一开始追求同等覆盖。

### 当前判断

短期不建议自研完整 AI NVR。优先通过 Frigate Bridge 复用 Frigate 检测结果。只有当 Lumos Home 的用户明确需要“无需 Frigate 的轻量本地识别”时，再做最小可用 AI 检测。

### 执行任务

- [ ] 明确目标硬件范围：CPU、Intel iGPU/OpenVINO、NVIDIA、Rockchip 中选一个起步。
- [ ] 选择模型格式：优先 ONNX 或 OpenVINO。
- [ ] 只支持少量标签：person、car、package。
- [ ] 检测结果写入 `camera_events`，不要另建一套并行事件体系。
- [ ] UI 上标记 AI 事件来源为 `lumos-ai`。
- [ ] 提供全局开关和每摄像头开关。
- [ ] 明确资源预算：最大检测 FPS、最大并发摄像头数、硬件不可用时降级。

### 验收标准

- AI 检测是可选模块，关闭后不影响基础 NVR。
- 检测失败不会影响直播和录制。
- 检测事件与 Frigate Bridge 事件使用同一事件模型。
- 用户可以理解当前使用的是 Lumos AI 还是 Frigate 外部检测。

## 不建议近期投入的方向

- 复制 Frigate 的完整对象检测器矩阵。
- 自研 WebRTC/RTSP server。
- 过早做复杂多模型管理。
- 直接把 Frigate 代码嵌入本项目。
- 把项目定位改成 Frigate 替代品。

## 推荐里程碑

### Milestone 1: 视频基础稳定

- 完成 `StreamManager`
- HLS 进程下沉服务层
- 统一流状态
- 完成基础资源限制和进程清理

### Milestone 2: 事件模型落地

- 新增 `camera_events`
- 录制关联事件
- 前端事件时间线初版
- 支持事件过滤和详情

### Milestone 3: 外部生态接入

- MQTT 发布内部事件
- Frigate Bridge 订阅外部事件
- Frigate 事件进入 Lumos 时间线
- 基于 Frigate 事件触发 NAS/DLNA/通知

### Milestone 4: NVR 体验增强

- 保留策略
- 锁定事件
- 缩略图
- 分段回放优化
- 批量管理

### Milestone 5: 智能能力扩展

- 区域/遮罩编辑
- 轻量运动检测
- 评估是否需要本地 AI 检测

## 近期建议先做的 5 个具体任务

1. 新增 `camera_events` 数据模型和 API 草案。
2. 抽出 `StreamManager`，先接管 HLS live start/stop。
3. 让手动录制创建 `manual_recording` 事件，并把录像分段关联到事件。
4. 增加 MQTT 配置与内部事件发布基础设施。
5. 实现 Frigate Bridge 的最小版本：订阅 Frigate 事件并写入 `camera_events`。

## 开放问题

- 是否要把 Frigate 作为官方推荐的高级视频后端？
- Windows 安装包是否内置 go2rtc？
- MQTT 是默认启用还是高级设置？
- 事件模型是否需要支持跨摄像头事件？
- NAS 同步是按录像文件同步，还是按事件目录同步？
- DLNA 自动投屏应该支持哪些事件类型？
- 轻量 motion detection 是否必须支持 Windows 无 GPU 环境？

