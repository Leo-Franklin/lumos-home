# 录像库文件路径显示优化设计

## 背景

当前录像库（RecordingsView）表格未显示录像文件名，也没有提供快速打开本地文件目录的功能。用户无法直观看到录像文件名称，也无法直接进入存放目录。

## 目标

1. 表格中显示录像文件名
2. 对于本地存储，点击可打开本机文件目录
3. 对于 NAS 存储，点击可打开 NAS 上的文件位置

## 后端改动

### `backend/app/schemas/recording.py`

`RecordingOut` 新增三个字段：

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
    # 新增
    storage_type: str  # "local" | "nas"
    nas_access_url: str | None  # NAS 时返回可访问的 URL（SMB/WebDAV/厂家协议），本地为 null
    file_name: str  # 从 file_path 提取的文件名
```

### 改动范围说明

- `storage_type`：由后端根据录像实际存储位置判断写入，`'local'` 或 `'nas'`
- `nas_access_url`：NAS 存储时后端返回完整的可访问 URL（smb://、http:// 等），本地存储时为 `null`
- `file_name`：后端从 `file_path` 提取文件名部分返回，前端直接使用

## 前端改动

### `src/views/RecordingsView.vue`

#### 1. 表格新增列

在现有操作列左侧新增一列：**文件**（包含文件名 + 打开文件夹按钮）

```html
<el-table-column :label="$t('recordings.file')" width="200">
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

#### 2. 打开文件夹逻辑

```js
function openFolder(row) {
  if (row.storage_type === 'local') {
    // 打开本机目录（file_path 为本机路径）
    window.open('file://' + row.file_path)
  } else if (row.storage_type === 'nas' && row.nas_access_url) {
    // 打开 NAS 地址（smb://、http:// 等）
    window.open(row.nas_access_url)
  }
}
```

#### 3. import 新增 FolderOpened 图标

```js
import { VideoCameraFilled, Clock, FolderOpened, VideoPlay, Download, Delete } from '@element-plus/icons-vue'
```

### `src/locales/zh-CN/recordings.js`

新增文案：

```js
file: '文件',
fileName: '文件名',
openFolder: '打开文件夹',
openLocalFolder: '打开本地文件夹',
openNasFolder: '打开 NAS 文件夹',
```

### `src/locales/en/recordings.js`

```js
file: 'File',
fileName: 'File Name',
openFolder: 'Open Folder',
openLocalFolder: 'Open Local Folder',
openNasFolder: 'Open NAS Folder',
```

### 样式改动 (`RecordingsView.vue` style 部分)

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

## 改动文件清单

| 文件 | 改动类型 |
|------|----------|
| `backend/app/schemas/recording.py` | 新增字段 |
| `src/views/RecordingsView.vue` | 表格列 + 打开逻辑 |
| `src/locales/zh-CN/recordings.js` | 国际化文案 |
| `src/locales/en/recordings.js` | 国际化文案 |

## 待确认

1. `nas_access_url` 的具体协议和格式——绿联 NAS 支持的协议确认后填充
2. 后端 `storage_type` 判断逻辑需实现（本地路径 vs NAS 路径的区分规则）
