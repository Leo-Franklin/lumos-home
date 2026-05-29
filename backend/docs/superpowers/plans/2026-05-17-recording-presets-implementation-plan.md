# 录制预设与分段录制实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为每台摄像机添加多个录制预设（分辨率、分段时长、码率、帧率），支持手动录制和计划录制时使用预设或临时覆盖参数。

**Architecture:**
- Camera 模型新增 `recording_presets` (JSON) 和 `default_preset_id` 字段
- Schedule 模型新增 `preset_id` 和 `overrides` 字段
- `/record/start` 支持 `preset_id` + `overrides` 参数覆盖
- Recorder 支持可配置的 FFmpeg 参数（分辨率、码率、帧率）
- 前端 CameraView 添加预设管理，ScheduleView 添加预设选择

**Tech Stack:** FastAPI (Python), SQLAlchemy, Vue 3 + Element Plus, FFmpeg

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `app/domain/models/camera.py` | 新增 `recording_presets`, `default_preset_id` 字段 |
| `app/domain/models/schedule.py` | 新增 `preset_id`, `overrides` 字段 |
| `app/domain/services/recorder.py` | 支持可变参数（resolution/bitrate/fps），修改 FFmpeg 命令生成 |
| `app/api/cameras.py` | 新增预设 CRUD 端点，修改 `record/start` 支持参数覆盖 |
| `app/api/schedules.py` | 修改 create/update 支持 `preset_id`, `overrides` |
| `app/schemas/camera.py` | 新增 `RecordingPreset` schema，`CameraOut` 含预设字段 |
| `app/schemas/schedule.py` | 新增 `preset_id`, `overrides` 字段 |
| `smart-home-frontend/src/views/CameraView.vue` | 添加预设管理 UI + 录制对话框 |
| `smart-home-frontend/src/views/ScheduleView.vue` | 添加预设选择 |
| `smart-home-frontend/src/api/cameras.js` | 新增预设 API |
| `smart-home-frontend/src/stores/cameras.js` | 管理预设状态 |
| `tests/test_recording_presets.py` | 新建预设相关测试 |

---

## Task 1: 数据模型 - Camera 预设字段

**Files:**
- Modify: `app/domain/models/camera.py:1-26`
- Modify: `app/schemas/camera.py:1-50`
- Test: `tests/test_recording_presets.py`

- [ ] **Step 1: 添加 RecordingPreset dataclass 和 Camera 字段**

修改 `app/domain/models/camera.py`，在 `Camera` 类末尾添加：

```python
# app/domain/models/camera.py 末尾添加
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class RecordingPreset:
    id: str
    name: str
    resolution: str = "1920x1080"      # 宽x高
    segment_duration: int = 600        # 秒
    bitrate: Optional[int] = None       # kbps，None=自动
    fps: Optional[int] = None          # None=25

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "resolution": self.resolution,
            "segment_duration": self.segment_duration,
            "bitrate": self.bitrate,
            "fps": self.fps,
        }

    @staticmethod
    def from_dict(data: dict) -> "RecordingPreset":
        return RecordingPreset(
            id=data["id"],
            name=data["name"],
            resolution=data.get("resolution", "1920x1080"),
            segment_duration=data.get("segment_duration", 600),
            bitrate=data.get("bitrate"),
            fps=data.get("fps"),
        )
```

然后在 `Camera` 类中添加两个新字段（在 `is_online` 之后）：

```python
    recording_presets: Mapped[list] = mapped_column(default=list)  # JSON 存储
    default_preset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
```

- [ ] **Step 2: 修改 Camera 模型以支持 JSON 序列化**

Camera 模型使用 `Mapped[list]` 存储 JSON，需要在 `__init__` 或属性访问时转换。在 `app/domain/models/camera.py` 末尾添加 helper 方法：

```python
    def get_presets(self) -> list[RecordingPreset]:
        import json
        if not self.recording_presets:
            return []
        if isinstance(self.recording_presets, list):
            return [RecordingPreset.from_dict(p) if isinstance(p, dict) else p for p in self.recording_presets]
        try:
            parsed = json.loads(self.recording_presets)
            return [RecordingPreset.from_dict(p) for p in parsed]
        except Exception:
            return []

    def set_presets(self, presets: list[RecordingPreset]):
        self.recording_presets = [p.to_dict() for p in presets]

    def add_preset(self, preset: RecordingPreset):
        presets = self.get_presets()
        presets.append(preset)
        self.set_presets(presets)

    def remove_preset(self, preset_id: str):
        presets = self.get_presets()
        self.recording_presets = [p for p in presets if p.id != preset_id]
        if self.default_preset_id == preset_id:
            self.default_preset_id = None

    def update_preset(self, preset_id: str, data: dict):
        presets = self.get_presets()
        for i, p in enumerate(presets):
            if p.id == preset_id:
                for key in ["name", "resolution", "segment_duration", "bitrate", "fps"]:
                    if key in data:
                        setattr(p, key, data[key])
                presets[i] = p
                break
        self.set_presets(presets)

    def get_default_preset(self) -> RecordingPreset | None:
        if not self.default_preset_id:
            return None
        presets = self.get_presets()
        return next((p for p in presets if p.id == self.default_preset_id), None)
```

- [ ] **Step 3: 更新 CameraOut schema**

修改 `app/schemas/camera.py`，添加 `RecordingPreset` schema 并更新 `CameraOut`：

```python
# app/schemas/camera.py

from typing import Optional

class RecordingPresetSchema(BaseModel):
    id: str
    name: str
    resolution: str = "1920x1080"
    segment_duration: int = 600
    bitrate: Optional[int] = None
    fps: Optional[int] = None

class CameraOut(BaseModel):
    id: int
    device_mac: str
    onvif_host: str
    onvif_port: int
    onvif_user: str | None
    rtsp_port: int
    rtsp_url: str | None
    stream_profile: str
    is_recording: bool
    is_online: bool
    last_probe_at: datetime | None
    auto_cast_dlna: str | None
    created_at: datetime
    recording_presets: list[RecordingPresetSchema] = []
    default_preset_id: str | None = None

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: 编写测试**

创建 `tests/test_recording_presets.py`：

```python
import pytest
from app.domain.models.camera import Camera, RecordingPreset

def test_recording_preset_to_dict():
    preset = RecordingPreset(
        id="test-123",
        name="室外-1080p",
        resolution="1920x1080",
        segment_duration=600,
        bitrate=2048,
        fps=25,
    )
    data = preset.to_dict()
    assert data["id"] == "test-123"
    assert data["name"] == "室外-1080p"
    assert data["resolution"] == "1920x1080"
    assert data["bitrate"] == 2048

def test_recording_preset_from_dict():
    data = {
        "id": "abc-456",
        "name": "室内-720p",
        "resolution": "1280x720",
        "segment_duration": 1800,
        "bitrate": None,
        "fps": 20,
    }
    preset = RecordingPreset.from_dict(data)
    assert preset.id == "abc-456"
    assert preset.resolution == "1280x720"
    assert preset.fps == 20

def test_camera_preset_management():
    cam = Camera(device_mac="AA:BB:CC:DD:EE:FF", onvif_host="192.168.1.100")
    assert cam.get_presets() == []

    preset = RecordingPreset(
        id="preset-1",
        name="测试预设",
        resolution="1920x1080",
        segment_duration=600,
    )
    cam.add_preset(preset)
    assert len(cam.get_presets()) == 1
    assert cam.get_presets()[0].name == "测试预设"

    cam.default_preset_id = "preset-1"
    default = cam.get_default_preset()
    assert default is not None
    assert default.id == "preset-1"

    cam.remove_preset("preset-1")
    assert len(cam.get_presets()) == 0
    assert cam.get_default_preset() is None

def test_camera_update_preset():
    cam = Camera(device_mac="AA:BB:CC:DD:EE:FF", onvif_host="192.168.1.100")
    preset = RecordingPreset(id="p1", name="原始名称", resolution="1920x1080", segment_duration=600)
    cam.add_preset(preset)

    cam.update_preset("p1", {"name": "新名称", "segment_duration": 1200})
    updated = cam.get_presets()[0]
    assert updated.name == "新名称"
    assert updated.segment_duration == 1200
    assert updated.resolution == "1920x1080"  # 未改动的字段保持不变
```

- [ ] **Step 5: 运行测试**

Run: `pytest tests/test_recording_presets.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: 提交**

```bash
git add app/domain/models/camera.py app/schemas/camera.py tests/test_recording_presets.py
git commit -m "feat(models): add RecordingPreset and camera preset fields

- Add RecordingPreset dataclass with id, name, resolution, segment_duration, bitrate, fps
- Add camera.recording_presets (JSON list) and default_preset_id fields
- Add helper methods: get_presets, add_preset, remove_preset, update_preset, get_default_preset
- Update CameraOut schema with recording_presets and default_preset_id"
```

---

## Task 2: 预设管理 API 端点

**Files:**
- Modify: `app/api/cameras.py:1-435`
- Test: `tests/test_recording_presets.py`

- [ ] **Step 1: 添加预设 API 端点**

在 `app/api/cameras.py` 末尾添加 5 个新端点：

```python
# app/api/cameras.py 末尾添加
import uuid

@router.get("/{mac}/presets")
async def list_presets(mac: str, db: DBDep, _: CurrentUser):
    result = await db.execute(select(Camera).where(Camera.device_mac == mac))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail="摄像头未配置")
    return camera.get_presets()

@router.post("/{mac}/presets", status_code=status.HTTP_201_CREATED)
async def create_preset(mac: str, body: dict, db: DBDep, _: CurrentUser):
    result = await db.execute(select(Camera).where(Camera.device_mac == mac))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail="摄像头未配置")

    preset = RecordingPreset(
        id=body.get("id", str(uuid.uuid4())),
        name=body["name"],
        resolution=body.get("resolution", "1920x1080"),
        segment_duration=body.get("segment_duration", 600),
        bitrate=body.get("bitrate"),
        fps=body.get("fps"),
    )
    camera.add_preset(preset)
    await db.commit()
    return preset.to_dict()

@router.put("/{mac}/presets/{preset_id}", status_code=status.HTTP_200_OK)
async def update_preset(mac: str, preset_id: str, body: dict, db: DBDep, _: CurrentUser):
    result = await db.execute(select(Camera).where(Camera.device_mac == mac))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail="摄像头未配置")

    presets = camera.get_presets()
    if not any(p.id == preset_id for p in presets):
        raise HTTPException(status_code=404, detail="预设不存在")

    camera.update_preset(preset_id, body)
    await db.commit()
    updated = next(p for p in camera.get_presets() if p.id == preset_id)
    return updated.to_dict()

@router.delete("/{mac}/presets/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preset(mac: str, preset_id: str, db: DBDep, _: CurrentUser):
    result = await db.execute(select(Camera).where(Camera.device_mac == mac))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail="摄像头未配置")

    presets = camera.get_presets()
    if not any(p.id == preset_id for p in presets):
        raise HTTPException(status_code=404, detail="预设不存在")

    camera.remove_preset(preset_id)
    await db.commit()

@router.put("/{mac}/presets/default", status_code=status.HTTP_200_OK)
async def set_default_preset(mac: str, body: dict, db: DBDep, _: CurrentUser):
    result = await db.execute(select(Camera).where(Camera.device_mac == mac))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail="摄像头未配置")

    preset_id = body.get("preset_id")
    if preset_id:
        presets = camera.get_presets()
        if not any(p.id == preset_id for p in presets):
            raise HTTPException(status_code=404, detail="预设不存在")

    camera.default_preset_id = preset_id
    await db.commit()
    return {"default_preset_id": camera.default_preset_id}
```

- [ ] **Step 2: 编写 API 测试**

在 `tests/test_recording_presets.py` 末尾添加：

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_crud_presets():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 首先创建摄像机
        resp = await ac.post("/api/v1/cameras", json={
            "device_mac": "11:22:33:44:55:66",
            "onvif_host": "192.168.1.50",
        })
        assert resp.status_code == 201

        mac = "11:22:33:44:55:66"

        # 创建预设
        resp = await ac.post(f"/api/v1/cameras/{mac}/presets", json={
            "name": "测试预设",
            "resolution": "1920x1080",
            "segment_duration": 600,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "测试预设"
        preset_id = data["id"]

        # 获取预设列表
        resp = await ac.get(f"/api/v1/cameras/{mac}/presets")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # 更新预设
        resp = await ac.put(f"/api/v1/cameras/{mac}/presets/{preset_id}", json={
            "name": "已更新",
            "segment_duration": 1200,
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "已更新"
        assert resp.json()["segment_duration"] == 1200

        # 设置默认
        resp = await ac.put(f"/api/v1/cameras/{mac}/presets/default", json={"preset_id": preset_id})
        assert resp.status_code == 200
        assert resp.json()["default_preset_id"] == preset_id

        # 删除预设
        resp = await ac.delete(f"/api/v1/cameras/{mac}/presets/{preset_id}")
        assert resp.status_code == 204

        resp = await ac.get(f"/api/v1/cameras/{mac}/presets")
        assert len(resp.json()) == 0
```

- [ ] **Step 3: 运行测试**

Run: `pytest tests/test_recording_presets.py -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add app/api/cameras.py tests/test_recording_presets.py
git commit -m "feat(api): add preset CRUD endpoints for cameras

- GET/POST /cameras/{mac}/presets - list and create
- PUT/DELETE /cameras/{mac}/presets/{id} - update and delete
- PUT /cameras/{mac}/presets/default - set default preset"
```

---

## Task 3: Schedule 模型扩展

**Files:**
- Modify: `app/domain/models/schedule.py:1-20`
- Modify: `app/schemas/schedule.py:1-31`
- Test: `tests/test_recording_presets.py`

- [ ] **Step 1: 添加 Schedule 字段**

修改 `app/domain/models/schedule.py`，在 `Schedule` 类中添加：

```python
# app/domain/models/schedule.py
    preset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    overrides: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 存储
```

添加 helper 方法：

```python
    def get_overrides(self) -> dict | None:
        import json
        if not self.overrides:
            return None
        try:
            return json.loads(self.overrides)
        except Exception:
            return None

    def set_overrides(self, data: dict | None):
        import json
        self.overrides = json.dumps(data) if data else None

    def get_effective_segment_duration(self) -> int:
        """兼容旧版：优先用 overrides.segment_duration，其次 self.segment_duration"""
        overrides = self.get_overrides()
        if overrides and "segment_duration" in overrides:
            return overrides["segment_duration"]
        return self.segment_duration
```

- [ ] **Step 2: 更新 Schedule schemas**

修改 `app/schemas/schedule.py`：

```python
class ScheduleCreate(BaseModel):
    camera_mac: str
    name: str | None = None
    cron_expr: str
    segment_duration: int = 1800
    enabled: bool = True
    preset_id: str | None = None
    overrides: dict | None = None


class ScheduleUpdate(BaseModel):
    name: str | None = None
    cron_expr: str | None = None
    segment_duration: int | None = None
    enabled: bool | None = None
    preset_id: str | None = None
    overrides: dict | None = None


class ScheduleOut(BaseModel):
    id: int
    camera_mac: str
    name: str | None
    cron_expr: str
    segment_duration: int
    enabled: bool
    created_at: datetime
    updated_at: datetime | None
    preset_id: str | None = None
    overrides: dict | None = None

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: 更新 API 端点**

修改 `app/api/schedules.py` 的 create 和 update 端点，在创建/更新时设置 `preset_id` 和 `overrides`。

- [ ] **Step 4: 测试**

添加测试验证 Schedule 的 preset_id 和 overrides 字段。

- [ ] **Step 5: 提交**

---

## Task 4: Recorder 支持可变参数（分辨率/码率/帧率）

**Files:**
- Modify: `app/domain/services/recorder.py:1-257`
- Modify: `app/domain/services/recording_domain.py`

- [ ] **Step 1: 定义 RecordingParams dataclass**

在 `recorder.py` 顶部添加：

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class RecordingParams:
    resolution: str = "1920x1080"
    segment_seconds: int = 1800
    bitrate: Optional[int] = None   # kbps
    fps: Optional[int] = None

    def bitrate_or_default(self) -> int:
        if self.bitrate:
            return self.bitrate
        # 自动匹配：基于分辨率
        w = int(self.resolution.split("x")[0])
        if w >= 1920:
            return 2048
        elif w >= 1280:
            return 1024
        else:
            return 512

    def fps_or_default(self) -> int:
        return self.fps or 25
```

- [ ] **Step 2: 修改 RecordingTask 添加 params**

```python
@dataclass
class RecordingTask:
    camera_mac: str
    process: subprocess.Popen
    output_path: Path
    started_at: datetime
    segment_seconds: int
    rtsp_url: str
    recording_id: int | None = None
    last_bytes: int = 0
    last_check: datetime | None = None
    session_start: datetime | None = None
    segment_index: int = 0
    params: RecordingParams = field(default_factory=RecordingParams)
```

- [ ] **Step 3: 修改 start_recording 签名**

```python
async def start_recording(self, camera_mac: str, rtsp_url: str, params: RecordingParams) -> str:
```

- [ ] **Step 4: 修改 FFmpeg 命令生成逻辑**

现有使用 `-c:v copy`，需要改为可配置参数：

```python
def _build_ffmpeg_cmd(self, rtsp_url: str, output_path: Path, params: RecordingParams) -> list:
    cmd = [
        "ffmpeg", "-y",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-c:v", "libx264",
        "-preset", "medium",
        "-b:v", f"{params.bitrate_or_default()}k",
        "-r", str(params.fps_or_default()),
        "-s", params.resolution,
        "-c:a", "aac",
        "-t", str(params.segment_seconds),
        "-movflags", "+frag_keyframe+empty_moov",
        str(output_path),
    ]
    return cmd
```

注意：由于 FFmpeg 参数变化，需要在 `_monitor_loop` 中重启 segment 时也使用同样的 `_build_ffmpeg_cmd` 方法。

- [ ] **Step 5: 更新 cameras.py 的 start_recording**

修改 `app/api/cameras.py` 的 `start_recording` 端点，接收可选的 `preset_id` 和 `overrides`，解析为 `RecordingParams` 并传递给 `recorder.start_recording`。

- [ ] **Step 6: 测试**

编写测试验证不同参数生成正确的 FFmpeg 命令。

- [ ] **Step 7: 提交**

---

## Task 5: 前端 - 预设管理 + 录制对话框

**Files:**
- Modify: `smart-home-frontend/src/api/cameras.js`
- Modify: `smart-home-frontend/src/stores/cameras.js`
- Modify: `smart-home-frontend/src/views/CameraView.vue`
- Test: 手动测试

- [ ] **Step 1: 添加 API 函数**

在 `src/api/cameras.js` 添加：

```javascript
// 预设管理
export const listPresets = (mac) => api.get(`/cameras/${mac}/presets`)
export const createPreset = (mac, data) => api.post(`/cameras/${mac}/presets`, data)
export const updatePreset = (mac, presetId, data) => api.put(`/cameras/${mac}/presets/${presetId}`, data)
export const deletePreset = (mac, presetId) => api.delete(`/cameras/${mac}/presets/${presetId}`)
export const setDefaultPreset = (mac, presetId) => api.put(`/cameras/${mac}/presets/default`, { preset_id: presetId })

// 修改 startRecord 支持参数
export const startRecord = (mac, { preset_id, overrides } = {}) =>
  api.post(`/cameras/${mac}/record/start`, { preset_id, overrides })
```

- [ ] **Step 2: 更新 cameras store**

在 `src/stores/cameras.js` 添加预设管理状态：

```javascript
// 在 useCamerasStore 中添加
const presets = ref({})  // { mac: [preset1, preset2] }
const defaultPresetId = ref({})  // { mac: presetId }

const loadPresets = async (mac) => {
  const res = await listPresets(mac)
  presets.value[mac] = res.data
}

const addPreset = async (mac, data) => {
  const res = await createPreset(mac, data)
  await loadPresets(mac)
  return res.data
}

const removePreset = async (mac, presetId) => {
  await deletePreset(mac, presetId)
  await loadPresets(mac)
}

const setDefault = async (mac, presetId) => {
  await setDefaultPreset(mac, presetId)
  defaultPresetId.value[mac] = presetId
}
```

- [ ] **Step 3: 更新 CameraView.vue**

在 CameraView.vue 中：
1. 添加"管理预设"按钮，打开预设管理对话框
2. 修改"开始录制"按钮，打开录制对话框（含预设选择 + 参数覆盖）
3. 预设管理对话框：列出预设、添加表单、编辑/删除、设默认
4. 录制对话框：预设选择卡片 + 参数覆盖表单 + 分段说明

- [ ] **Step 4: 测试**

手动测试预设创建、编辑、删除、设默认，以及开始录制时选择预设。

- [ ] **Step 5: 提交**

---

## Task 6: 前端 - ScheduleView 预设选择

**Files:**
- Modify: `smart-home-frontend/src/views/ScheduleView.vue`
- Modify: `smart-home-frontend/src/api/schedules.js`

- [ ] **Step 1: 更新 schedules API**

```javascript
export const createSchedule = (data) => api.post("/schedules", data)
export const updateSchedule = (id, data) => api.patch(`/schedules/${id}`, data)
// 现有的 list, delete 保持不变
```

- [ ] **Step 2: 更新 ScheduleView.vue**

在计划创建/编辑表单中添加：
1. 预设选择下拉框（加载当前摄像机的预设列表）
2. 覆盖参数区域（当选择预设后可调整）

- [ ] **Step 3: 测试**

手动测试创建计划时选择预设。

- [ ] **Step 4: 提交**

---

## Task 7: 集成测试 + 修复

**Files:**
- Test: `tests/test_recording_presets.py`

- [ ] **Step 1: 编写端到端测试**

测试完整的录制流程：创建摄像机 → 添加预设 → 开始录制 → 验证参数 → 停止录制。

- [ ] **Step 2: 修复发现的问题**

根据测试结果修复。

- [ ] **Step 3: 提交**

---

## 依赖关系

```
Task 1 (Camera模型) ──────────────────────┐
                                           ├─> Task 2 (预设API) ──> Task 7 (集成测试)
Task 4 (Recorder参数) ─────────────────────┤
                                           │
Task 3 (Schedule模型) ──────────────────────> Task 5 (前端CameraView)
Task 6 (前端ScheduleView) ──────────────────┘
```

---

## 验证计划

1. **单元测试**: `pytest tests/test_recording_presets.py -v` 全部通过
2. **API 测试**: 预设 CRUD 端点全部 200/201/204
3. **手动测试**:
   - CameraView 预设管理正常
   - 开始录制选择预设并验证文件参数
   - ScheduleView 创建带预设的计划

---

**Plan complete.** 7 tasks, each producing independently testable software.

Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
