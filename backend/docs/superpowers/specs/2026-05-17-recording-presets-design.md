# 录制预设与分段录制设计

**日期**: 2026-05-17
**状态**: 已批准

## 1. 概述

为 smart-home 系统添加录制预设管理功能，支持：
- 每台摄像机保存多个录制预设（分辨率、分段时长、码率、帧率）
- 手动录制和计划录制均可使用预设
- 支持临时覆盖预设参数

## 2. 功能需求

### 2.1 摄像机预设管理
- 每台摄像机可保存多个命名预设
- 每个预设包含：名称、分辨率、分段时长、码率、帧率
- 可设置一个默认预设
- 预设保存在摄像机配置中（JSON 格式）

### 2.2 手动录制
- 开始录制时选择预设或自定义参数
- 支持临时覆盖所有预设参数
- 按设置的分段时长自动切割视频（生成多个文件）

### 2.3 计划录制
- 创建计划时选择预设
- 支持临时覆盖预设参数
- 按 Cron 表达式定时执行，使用配置的参数录制

## 3. 数据模型

### 3.1 Camera 预设字段
```python
# app/domain/models/camera.py
class Camera:
    # 新增字段
    recording_presets: List[RecordingPreset] = []  # 预设列表
    default_preset_id: Optional[str] = None        # 默认预设ID
```

### 3.2 RecordingPreset 模型
```python
@dataclass
class RecordingPreset:
    id: str                           # UUID
    name: str                         # 如 "室外-1080p"
    resolution: str                   # "1920x1080"
    segment_duration: int              # 秒
    bitrate: Optional[int]            # kbps，None=自动
    fps: Optional[int]                # None=25
```

### 3.3 Schedule 扩展
```python
# app/domain/models/schedule.py
class Schedule:
    # 新增字段
    preset_id: Optional[str] = None   # 使用的预设ID
    overrides: Optional[dict] = None  # 覆盖参数
```

## 4. API 设计

### 4.1 预设管理
```
GET    /cameras/{mac}/presets          # 获取预设列表
POST   /cameras/{mac}/presets          # 添加预设
PUT    /cameras/{mac}/presets/{id}     # 更新预设
DELETE /cameras/{mac}/presets/{id}     # 删除预设
PUT    /cameras/{mac}/presets/default  # 设置默认预设
```

### 4.2 手动录制
```
POST   /cameras/{mac}/record/start
Body: {
    "preset_id": "xxx",              # 可选，使用预设
    "overrides": {                   # 可选，覆盖参数
        "resolution": "1920x1080",
        "segment_duration": 600,
        "bitrate": 2048,
        "fps": 25
    }
}
```

### 4.3 计划录制
```
POST   /schedules
Body: {
    "camera_mac": "xxx",
    "name": "每日巡逻",
    "cron_expr": "0 8 * * 1-5",
    "preset_id": "xxx",              # 可选
    "overrides": {},                 # 可选
    "segment_duration": 600,         # 兼容旧版
    "enabled": true
}
```

## 5. 前端实现

### 5.1 预设管理组件
- 位置：`src/components/RecordingPresets.vue` 或集成到 CameraView
- 功能：列出预设、添加/编辑/删除、设默认
- 样式：深色主题，Element Plus 风格

### 5.2 手动录制对话框
- 位置：CameraView.vue 开始录制按钮
- 功能：预设选择 + 参数覆盖表单
- 分段说明提示

### 5.3 计划录制表单
- 位置：ScheduleView.vue
- 修改：添加预设选择器和参数覆盖区

## 6. 后端实现

### 6.1 录制参数解析优先级
1. overrides（手动覆盖）
2. preset_id（预设配置）
3. 摄像机默认配置
4. 全局默认（recording_segment_seconds）

### 6.2 FFmpeg 参数生成
```python
def build_ffmpeg_args(camera: Camera, params: RecordingParams) -> list:
    resolution = params.resolution or get_default_resolution(camera)
    bitrate = params.bitrate or get_auto_bitrate(resolution)

    return [
        '-rtsp_transport', 'tcp',
        '-i', camera.rtsp_uri,
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-b:v', f'{bitrate}k',
        '-r', str(params.fps or 25),
        '-s', resolution,
        '-c:a', 'aac',
        '-t', str(params.segment_duration),
        '-movflags', '+frag_keyframe+empty_moov',
        output_path
    ]
```

## 7. 分段录制逻辑

录制开始后，Recorder 循环：
1. 检查 `is_recording` 标志
2. 调用 `should_continue_cb(mac)` 判断是否继续
3. 若继续，生成新分段文件
4. 若停止，等待当前分段完成，触发 NAS 同步

分段文件命名：`{camera_mac}_{start_timestamp}_{segment_index}.mp4`

## 8. 影响范围

| 文件 | 改动 |
|------|------|
| `app/domain/models/camera.py` | 新增 `recording_presets`, `default_preset_id` |
| `app/domain/models/schedule.py` | 新增 `preset_id`, `overrides` |
| `app/api/cameras.py` | 新增预设 CRUD 端点，修改 record/start |
| `app/api/schedules.py` | 修改 create/update 支持 preset_id |
| `app/domain/services/recorder.py` | 支持参数覆盖 |
| `smart-home-frontend/src/views/CameraView.vue` | 添加预设管理、录制对话框 |
| `smart-home-frontend/src/views/ScheduleView.vue` | 添加预设选择 |

## 9. 兼容性

- 现有 `/record/start` 继续有效（使用全局默认）
- 现有 Schedule 继续有效（忽略 preset_id）
- 向后兼容，无需数据迁移
