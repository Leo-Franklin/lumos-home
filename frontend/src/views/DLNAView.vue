<script setup>
import { ref, computed, onMounted } from 'vue'
import { useDLNAStore } from '@/stores/dlna'
import { castURL, castFile, playDevice, pauseDevice, stopDevice } from '@/api/dlna'
import { ElMessage } from 'element-plus'
import { Search, VideoPlay, VideoPause, SwitchButton, Refresh, Upload, Link } from '@element-plus/icons-vue'

const dlna = useDLNAStore()

const castMode = ref('url')
const mediaUrl = ref('')
const fileList = ref([])
const castLoading = ref(false)
const playLoading = ref(false)
const statusTimer = ref(null)

onMounted(() => {
  dlna.fetchDevices()
})

const stateLabel = computed(() => {
  const s = dlna.transportState?.current_transport_state
  if (!s) return '--'
  const map = { PLAYING: '播放中', PAUSED_PLAYBACK: '已暂停', STOPPED: '已停止', NO_MEDIA_PRESENT: '无媒体', TRANSITIONING: '切换中' }
  return map[s] ?? s
})

const stateType = computed(() => {
  const s = dlna.transportState?.current_transport_state
  if (s === 'PLAYING') return 'success'
  if (s === 'PAUSED_PLAYBACK') return 'warning'
  if (s === 'STOPPED') return 'info'
  return ''
})

async function handleCast() {
  if (!dlna.selectedDevice) return
  castLoading.value = true
  try {
    if (castMode.value === 'url') {
      if (!mediaUrl.value.trim()) {
        ElMessage.warning('请输入媒体 URL')
        return
      }
      await castURL({ device_id: dlna.selectedDevice.id, media_url: mediaUrl.value.trim() })
      ElMessage.success('投屏指令已发送')
    } else {
      if (!fileList.value.length) {
        ElMessage.warning('请选择要投屏的文件')
        return
      }
      const formData = new FormData()
      formData.append('device_id', dlna.selectedDevice.id)
      formData.append('file', fileList.value[0].raw)
      await castFile(formData)
      ElMessage.success('文件投屏指令已发送')
      fileList.value = []
    }
    await dlna.refreshStatus()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '投屏失败')
  } finally {
    castLoading.value = false
  }
}

async function handlePlay() {
  if (!dlna.selectedDevice) return
  playLoading.value = true
  try {
    await playDevice(dlna.selectedDevice.id)
    ElMessage.success('播放')
    await dlna.refreshStatus()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    playLoading.value = false
  }
}

async function handlePause() {
  if (!dlna.selectedDevice) return
  playLoading.value = true
  try {
    await pauseDevice(dlna.selectedDevice.id)
    ElMessage.success('已暂停')
    await dlna.refreshStatus()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    playLoading.value = false
  }
}

async function handleStop() {
  if (!dlna.selectedDevice) return
  playLoading.value = true
  try {
    await stopDevice(dlna.selectedDevice.id)
    ElMessage.success('已停止')
    await dlna.refreshStatus()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    playLoading.value = false
  }
}

function beforeUpload() {
  return false
}

function handleFileChange(file) {
  fileList.value = [file]
}

function handleFileRemove() {
  fileList.value = []
}
</script>

<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">超级遥控器</h2>
      <div class="page-header-actions">
        <el-button
          :loading="dlna.discovering"
          :icon="Search"
          @click="dlna.discover()"
        >
          {{ dlna.discovering ? '正在搜索...' : '搜索 DLNA 设备' }}
        </el-button>
        <el-button :icon="Refresh" circle @click="dlna.fetchDevices()" />
      </div>
    </div>

    <div class="dlna-layout">
      <!-- 左侧：设备列表 -->
      <div class="dlna-device-panel">
        <div class="panel-header">
          <span class="panel-title">已发现设备</span>
          <el-tag size="small" type="info">{{ dlna.devices.length }}</el-tag>
        </div>

        <div v-if="dlna.discovering" class="discover-tip">
          <el-icon class="is-loading"><Refresh /></el-icon>
          <span>SSDP 广播搜索中…</span>
        </div>

        <div v-if="dlna.devices.length === 0 && !dlna.discovering && !dlna.loading" class="empty-tip">
          <el-icon :size="32" style="color: var(--color-text-muted)"><Monitor /></el-icon>
          <p>未发现 DLNA 设备</p>
          <p class="sub">点击「搜索 DLNA 设备」开始扫描</p>
        </div>

        <div
          v-for="device in dlna.devices"
          :key="device.id"
          class="device-item"
          :class="{ selected: dlna.selectedDevice?.id === device.id }"
          @click="dlna.selectDevice(device)"
        >
          <div class="device-icon">
            <el-icon :size="20"><Monitor /></el-icon>
          </div>
          <div class="device-info">
            <div class="device-name">{{ device.friendly_name }}</div>
            <div class="device-meta">{{ device.ip }}</div>
            <div v-if="device.manufacturer" class="device-meta">{{ device.manufacturer }}</div>
          </div>
          <div class="device-status">
            <span class="status-dot" :class="device.is_online ? 'online' : 'offline'" />
          </div>
        </div>
      </div>

      <!-- 右侧：控制面板 -->
      <div class="dlna-control-panel">
        <div v-if="!dlna.selectedDevice" class="no-selection">
          <el-icon :size="48" style="color: var(--color-text-muted)"><VideoPlay /></el-icon>
          <p>请在左侧选择一个 DLNA 设备</p>
        </div>

        <template v-else>
          <!-- 设备信息卡 -->
          <div class="control-section">
            <div class="section-title">当前设备</div>
            <div class="device-card">
              <div class="device-card-left">
                <div class="device-card-icon">
                  <el-icon :size="22"><Monitor /></el-icon>
                </div>
                <div>
                  <div class="device-card-name">{{ dlna.selectedDevice.friendly_name }}</div>
                  <div class="device-card-meta">{{ dlna.selectedDevice.ip }}</div>
                  <div v-if="dlna.selectedDevice.model_name" class="device-card-meta">{{ dlna.selectedDevice.model_name }}</div>
                </div>
              </div>
              <div class="device-card-state">
                <el-tag v-if="dlna.transportState" :type="stateType" size="small">{{ stateLabel }}</el-tag>
                <el-button
                  :loading="dlna.statusLoading"
                  :icon="Refresh"
                  size="small"
                  circle
                  style="margin-left: 6px"
                  @click="dlna.refreshStatus()"
                />
              </div>
            </div>
          </div>

          <!-- 投屏控制 -->
          <div class="control-section">
            <div class="section-title">投屏内容</div>
            <el-radio-group v-model="castMode" style="margin-bottom: 12px">
              <el-radio-button value="url">
                <el-icon style="margin-right: 4px"><Link /></el-icon>网络 URL
              </el-radio-button>
              <el-radio-button value="file">
                <el-icon style="margin-right: 4px"><Upload /></el-icon>本地文件
              </el-radio-button>
            </el-radio-group>

            <div v-if="castMode === 'url'" class="cast-url-row">
              <el-input
                v-model="mediaUrl"
                placeholder="输入媒体 URL，如 http://example.com/video.mp4"
                clearable
                @keyup.enter="handleCast"
              />
            </div>

            <div v-else class="cast-file-row">
              <el-upload
                :auto-upload="false"
                :file-list="fileList"
                :before-upload="beforeUpload"
                :on-change="handleFileChange"
                :on-remove="handleFileRemove"
                :limit="1"
                accept="video/*,audio/*,image/*"
                drag
              >
                <el-icon class="el-icon--upload"><Upload /></el-icon>
                <div class="el-upload__text">拖拽文件至此，或 <em>点击上传</em></div>
                <template #tip>
                  <div class="el-upload__tip">支持视频、音频、图片格式</div>
                </template>
              </el-upload>
            </div>

            <el-button
              type="primary"
              :loading="castLoading"
              style="margin-top: 12px; width: 100%"
              @click="handleCast"
            >
              开始投屏
            </el-button>
          </div>

          <!-- 播放控制 -->
          <div class="control-section">
            <div class="section-title">播放控制</div>
            <div class="playback-controls">
              <el-button
                type="success"
                :icon="VideoPlay"
                :loading="playLoading"
                size="large"
                @click="handlePlay"
              >播放</el-button>
              <el-button
                type="warning"
                :icon="VideoPause"
                :loading="playLoading"
                size="large"
                @click="handlePause"
              >暂停</el-button>
              <el-button
                type="danger"
                :icon="SwitchButton"
                :loading="playLoading"
                size="large"
                @click="handleStop"
              >停止</el-button>
            </div>
          </div>

          <!-- 传输状态详情 -->
          <div v-if="dlna.transportState" class="control-section">
            <div class="section-title">传输状态</div>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="播放状态">
                <el-tag :type="stateType" size="small">{{ stateLabel }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="速度">{{ dlna.transportState.speed || '--' }}</el-descriptions-item>
              <el-descriptions-item label="状态码" :span="2">{{ dlna.transportState.status || '--' }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dlna-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
  align-items: start;
}

/* ── 左侧设备列表 ── */
.dlna-device-panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--color-border);
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-primary);
}

.discover-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.empty-tip {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 13px;
}
.empty-tip p { margin: 8px 0 0; }
.empty-tip .sub { font-size: 12px; color: var(--color-text-muted); margin-top: 4px; }

.device-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
  transition: background var(--duration-fast) ease-out;
  border-bottom: 1px solid var(--color-border);
}
.device-item:last-child { border-bottom: none; }
.device-item:hover { background: var(--color-surface-raised); }
.device-item.selected {
  background: var(--color-primary-subtle);
  border-left: 2px solid var(--color-primary);
  padding-left: 12px;
}

.device-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: var(--color-surface-raised);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--color-text-secondary);
}
.device-item.selected .device-icon { color: var(--color-primary); }

.device-info { flex: 1; min-width: 0; }
.device-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.device-meta {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 2px;
}

.device-status { flex-shrink: 0; }
.status-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: var(--radius-full);
}
.status-dot.online { background: var(--color-online); }
.status-dot.offline { background: var(--color-offline); }

/* ── 右侧控制面板 ── */
.dlna-control-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.no-selection {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80px 20px;
  color: var(--color-text-muted);
  font-size: 14px;
  gap: 12px;
}

.control-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 16px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
  margin-bottom: 12px;
}

.device-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.device-card-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.device-card-icon {
  width: 42px;
  height: 42px;
  border-radius: var(--radius-md);
  background: rgba(94, 92, 230, 0.10);
  border: 1px solid rgba(94, 92, 230, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
  flex-shrink: 0;
}
.device-card-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.device-card-meta {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 2px;
}
.device-card-state {
  display: flex;
  align-items: center;
}

.cast-url-row { display: flex; align-items: center; gap: 8px; }
.cast-file-row { margin-top: 4px; }

.playback-controls {
  display: flex;
  gap: 10px;
}
.playback-controls .el-button { flex: 1; }
</style>
