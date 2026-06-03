# 录像库文件路径显示优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在录像库表格中显示文件名，点击可打开本地文件夹或 NAS 文件夹

**Architecture:** 后端在 `RecordingOut` 新增 `storage_type`、`nas_access_url`、`file_name` 字段，前端新增表格列展示文件名和打开文件夹按钮。

**Tech Stack:** Vue 3 + Element Plus（前端）, FastAPI + Pydantic（后端）

---

## 文件结构

```
backend/app/
  schemas/recording.py       # 新增三个字段
  routers/recordings.py       # list_recordings 返回新字段

frontend/src/
  views/RecordingsView.vue   # 表格新增列 + openFolder 逻辑
  locales/zh-CN/recordings.js # 国际化新增
  locales/en/recordings.js    # 国际化新增
```

---

## Task 1: 后端 — 更新 RecordingOut Schema

**Files:**
- Modify: `D:/Project/Demo/smart_home/backend/app/schemas/recording.py:5-17`

- [ ] **Step 1: 修改 RecordingOut 新增三个字段**

将 `backend/app/schemas/recording.py` 第 5-17 行替换为：

```python
class RecordingOut(BaseModel):
    id: int
    camera_mac: str
    file_path: str
    file_size: int | None
    duration: int | None
    started_at: datetime
    ended_at: datetime | None
    status: str
    error_msg: str | None
    created_at: datetime
    # 新增字段
    storage_type: str  # "local" | "nas"
    nas_access_url: str | None  # NAS 时返回可访问 URL，本地为 None
    file_name: str  # 从 file_path 提取的文件名
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/schemas/recording.py
git commit -m "feat(api): add storage_type, nas_access_url, file_name to RecordingOut"
```

---

## Task 2: 后端 — 更新 list_recordings 计算新字段

**Files:**
- Modify: `D:/Project/Demo/smart_home/backend/app/routers/recordings.py:17-41`

**前置理解：**
- `settings.nas_mode` 可为 `"local"` | `"mount"` | `"smb"`
- `settings.local_storage_path` 是本地存储根目录
- `settings.nas_mount_path` 是 NAS 挂载路径
- `settings.nas_smb_host` / `settings.nas_smb_share` 是 SMB 配置
- `file_path` 是 `Recording.file_path`，可能是本地路径或 UNC 路径

**storage_type 判断逻辑：**
- 如果 `nas_mode == "local"` → `storage_type = "local"`
- 如果 `nas_mode in ("mount", "smb")` 且 `file_path` 以 `nas_mount_path` 开头 → `storage_type = "nas"`
- 否则 → `storage_type = "local"`

**nas_access_url 构造逻辑（smb 模式）：**
- `nas_mode == "smb"` 时，`file_path` 可能是 `\\192.168.1.100\share\folder\file.mp4`
- 转换为 `smb://192.168.1.100/share/folder/file.mp4`
- `nas_mode == "mount"` 时，`nas_access_url = None`（挂载路径前端无法直接访问）

- [ ] **Step 1: 在 list_recordings 函数中构造新字段**

在 `backend/app/routers/recordings.py` 第 36 后（`items = result.scalars().all()` 之后）添加辅助函数和字段计算逻辑。

在文件顶部 `from app.config import get_settings` 之后添加辅助函数：

```python
def _compute_recording_extra(file_path: str, settings) -> tuple[str, str | None, str]:
    """返回 (storage_type, nas_access_url, file_name)"""
    import os

    file_name = os.path.basename(file_path)
    local_storage = str(Path(settings.local_storage_path).resolve())
    nas_mount = settings.nas_mount_path.rstrip("/")

    if settings.nas_mode == "local":
        storage_type = "local"
        nas_access_url = None
    elif settings.nas_mode == "mount":
        if file_path.startswith(nas_mount) or nas_mount in file_path:
            storage_type = "nas"
            nas_access_url = None  # 挂载路径，前端无法直接打开
        else:
            storage_type = "local"
            nas_access_url = None
    elif settings.nas_mode == "smb":
        # UNC 路径：\\host\share\... → smb://host/share/...
        if file_path.startswith("\\\\"):
            storage_type = "nas"
            parts = file_path[2:].split("\\", 2)
            if len(parts) >= 2:
                host, share = parts[0], parts[1]
                rest = parts[2] if len(parts) > 2 else ""
                nas_access_url = f"smb://{host}/{share}/{rest}".rstrip("/")
            else:
                nas_access_url = None
        elif file_path.startswith(nas_mount):
            storage_type = "nas"
            # 挂载模式下，尝试从 smb_host/share 构造 URL
            if settings.nas_smb_host and settings.nas_smb_share:
                rel = file_path[len(nas_mount):].lstrip("/")
                nas_access_url = f"smb://{settings.nas_smb_host}/{settings.nas_smb_share}/{rel}".rstrip("/")
            else:
                nas_access_url = None
        else:
            storage_type = "local"
            nas_access_url = None
    else:
        storage_type = "local"
        nas_access_url = None

    return storage_type, nas_access_url, file_name
```

然后修改 `list_recordings` 函数，在 `items = result.scalars().all()` 之后构建新字段：

```python
    items = result.scalars().all()
    settings = get_settings()

    records = []
    for r in items:
        storage_type, nas_access_url, file_name = _compute_recording_extra(r.file_path, settings)
        records.append(RecordingOut(
            id=r.id,
            camera_mac=r.camera_mac,
            file_path=r.file_path,
            file_size=r.file_size,
            duration=r.duration,
            started_at=r.started_at,
            ended_at=r.ended_at,
            status=r.status,
            error_msg=r.error_msg,
            created_at=r.created_at,
            storage_type=storage_type,
            nas_access_url=nas_access_url,
            file_name=file_name,
        ))

    return PagedResponse(
        items=records, total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )
```

- [ ] **Step 2: 更新 get_recording 也返回新字段**

同样在 `backend/app/routers/recordings.py` 的 `get_recording` 函数（第 67-73 行）中加入新字段：

```python
@router.get("/{recording_id}", response_model=RecordingOut)
async def get_recording(recording_id: int, db: DBDep, _: CurrentUser):
    result = await db.execute(select(Recording).where(Recording.id == recording_id))
    recording = result.scalar_one_or_none()
    if not recording:
        raise HTTPException(status_code=404, detail="录像不存在")
    settings = get_settings()
    storage_type, nas_access_url, file_name = _compute_recording_extra(recording.file_path, settings)
    return RecordingOut(
        id=recording.id,
        camera_mac=recording.camera_mac,
        file_path=recording.file_path,
        file_size=recording.file_size,
        duration=recording.duration,
        started_at=recording.started_at,
        ended_at=recording.ended_at,
        status=recording.status,
        error_msg=recording.error_msg,
        created_at=recording.created_at,
        storage_type=storage_type,
        nas_access_url=nas_access_url,
        file_name=file_name,
    )
```

- [ ] **Step 3: 确保 Path import 存在**

在 `backend/app/routers/recordings.py` 顶部，确认 `from pathlib import Path` 已存在（第 6 行）。

- [ ] **Step 4: 提交**

```bash
git add backend/app/routers/recordings.py
git commit -m "feat(api): compute storage_type, nas_access_url, file_name for recordings endpoints"
```

---

## Task 3: 前端 — RecordingsView.vue 表格新增列

**Files:**
- Modify: `D:/Project/Demo/smart_home/smart-home-frontend/src/views/RecordingsView.vue`

- [ ] **Step 1: import 新增 FolderOpened 图标**

第 9 行改为：
```js
import { VideoCameraFilled, Clock, FolderOpened, VideoPlay, Download, Delete } from '@element-plus/icons-vue'
```

- [ ] **Step 2: 新增 openFolder 函数**

在 `closePlay` 函数之后（第 105 行附近）添加：

```js
function openFolder(row) {
  if (row.storage_type === 'local') {
    window.open('file://' + row.file_path)
  } else if (row.storage_type === 'nas' && row.nas_access_url) {
    window.open(row.nas_access_url)
  }
}
```

- [ ] **Step 3: 表格新增文件列**

在 `RecordingsView.vue` 模板的 `<el-table>` 内，在 `camera_mac` 列之后、`startTime` 列之前插入新列：

```html
<el-table-column :label="$t('recordings.file')" width="220">
  <template #default="{ row }">
    <div class="file-cell">
      <span class="file-name" :title="row.file_name">{{ row.file_name }}</span>
      <el-tooltip :content="row.storage_type === 'local' ? $t('recordings.openLocalFolder') : $t('recordings.openNasFolder')" :show-after="400">
        <el-button
          class="action-btn"
          size="small"
          :icon="FolderOpened"
          @click="openFolder(row)"
        />
      </el-tooltip>
    </div>
  </template>
</el-table-column>
```

新列插入在第 199 行 `camera_mac` 列之后。

- [ ] **Step 4: 添加 file-cell 样式**

在 `RecordingsView.vue` 的 `<style scoped>` 部分，在 `.action-group` 样式之后添加：

```css
.file-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.file-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}
```

- [ ] **Step 5: 提交**

```bash
git add src/views/RecordingsView.vue
git commit -m "feat(ui): add file name column with open folder button to recordings table"
```

---

## Task 4: 前端 — 国际化文案

**Files:**
- Modify: `D:/Project/Demo/smart_home/smart-home-frontend/src/locales/zh-CN/recordings.js`
- Modify: `D:/Project/Demo/smart_home/smart-home-frontend/src/locales/en/recordings.js`

- [ ] **Step 1: 中文文案**

在 `D:/Project/Demo/smart_home/smart-home-frontend/src/locales/zh-CN/recordings.js` 第 42 行后添加：

```js
  file: '文件',
  openLocalFolder: '打开本地文件夹',
  openNasFolder: '打开 NAS 文件夹',
```

- [ ] **Step 2: 英文文案**

在 `D:/Project/Demo/smart_home/smart-home-frontend/src/locales/en/recordings.js` 文件中添加对应英文：

```js
  file: 'File',
  openLocalFolder: 'Open Local Folder',
  openNasFolder: 'Open NAS Folder',
```

- [ ] **Step 3: 提交**

```bash
git add src/locales/zh-CN/recordings.js src/locales/en/recordings.js
git commit -m "feat(i18n): add file and folder open labels to recordings locale"
```

---

## 自检清单

- [ ] `RecordingOut` 有 `storage_type`、`nas_access_url`、`file_name` 三个新字段
- [ ] `list_recordings` 和 `get_recording` 接口返回新字段
- [ ] `storage_type` 正确区分 `local` 和 `nas`
- [ ] SMB 模式的 `nas_access_url` 正确将 UNC 路径转换为 `smb://` URL
- [ ] 前端表格新增"文件"列，显示 `file_name`
- [ ] 点击文件夹图标正确调用 `openFolder(row)`
- [ ] 国际化中英文案已添加
- [ ] 所有改动已提交
