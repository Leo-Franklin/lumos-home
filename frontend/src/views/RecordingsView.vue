<script setup>
import { ref, onMounted, watch } from 'vue'
import {
  listRecordings, deleteRecording, streamUrl, downloadUrl,
  requestRecordingHls, recordingHlsUrl, getRecordingStats,
} from '@/api/recordings'
import { listCameras } from '@/api/cameras'
import { ElMessage, ElMessageBox } from 'element-plus'
import CameraPlayer from '@/components/CameraPlayer.vue'
import { useNotificationsStore } from '@/stores/notifications'

const recordings = ref([])
const total = ref(0)
const loading = ref(false)
const cameras = ref([])
const notifications = useNotificationsStore()

const filter = ref({ camera_mac: '', date: '', page: 1, page_size: 20 })

onMounted(async () => {
  const { data } = await listCameras()
  cameras.value = data
  fetchRecordings()
})

watch(() => notifications.lastRecordingEvent, () => { fetchRecordings() })

async function fetchRecordings() {
  loading.value = true
  try {
    const params = { page: filter.value.page, page_size: filter.value.page_size }
    if (filter.value.camera_mac) params.camera_mac = filter.value.camera_mac
    if (filter.value.date) params.date = filter.value.date
    const { data } = await listRecordings(params)
    recordings.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

// ── Playback (B4: HLS) ────────────────────────────────────────
const playDialog = ref(false)
const playUrl = ref('')
const playMode = ref('recorded')
const hlsConvertingId = ref(null)
let hlsPollTimer = null

async function playRecording(rec) {
  try {
    const res = await requestRecordingHls(rec.id)
    if (res.status === 200) {
      playUrl.value = recordingHlsUrl(rec.id)
      playMode.value = 'hls'
      playDialog.value = true
    }
  } catch (e) {
    if (e.response?.status === 202) {
      ElMessage.info('录像转码中，请稍候...')
      hlsConvertingId.value = rec.id
      pollHlsReady(rec)
    } else {
      // fallback: direct stream
      const token = localStorage.getItem('token')
      playUrl.value = streamUrl(rec.id) + `?token=${token}`
      playMode.value = 'recorded'
      playDialog.value = true
    }
  }
}

function pollHlsReady(rec) {
  if (hlsPollTimer) clearInterval(hlsPollTimer)
  hlsPollTimer = setInterval(async () => {
    try {
      const res = await requestRecordingHls(rec.id)
      if (res.status === 200) {
        clearInterval(hlsPollTimer)
        hlsPollTimer = null
        hlsConvertingId.value = null
        ElMessage.success('转码完成，即将播放')
        playUrl.value = recordingHlsUrl(rec.id)
        playMode.value = 'hls'
        playDialog.value = true
      }
    } catch (e) {
      if (e.response?.status !== 202) {
        clearInterval(hlsPollTimer)
        hlsPollTimer = null
        hlsConvertingId.value = null
        ElMessage.error('转码失败')
      }
    }
  }, 3000)
}

function closePlay() {
  playUrl.value = ''
}

async function handleDelete(rec) {
  try {
    await ElMessageBox.confirm('确定删除该录像？', '确认删除', { type: 'warning' })
  } catch { return }
  try {
    await deleteRecording(rec.id)
    ElMessage.success('已删除')
    fetchRecordings()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '删除失败，请稍后重试')
  }
}

function downloadRecording(rec) {
  const token = localStorage.getItem('token')
  const url = downloadUrl(rec.id) + `?token=${token}`
  const a = document.createElement('a')
  a.href = url
  a.download = `recording_${rec.id}.mp4`
  a.click()
}

// ── Stats (C2) ───────────────────────────────────────────────
const statsDialog = ref(false)
const statsFilter = ref({ range: '7d', camera_mac: '' })
const statsData = ref(null)
const statsLoading = ref(false)

async function openStats() {
  statsDialog.value = true
  await fetchStats()
}

async function fetchStats() {
  statsLoading.value = true
  statsData.value = null
  try {
    const params = { range: statsFilter.value.range }
    if (statsFilter.value.camera_mac) params.camera_mac = statsFilter.value.camera_mac
    const { data } = await getRecordingStats(params)
    statsData.value = data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '统计加载失败')
  } finally {
    statsLoading.value = false
  }
}

function formatSize(bytes) {
  if (!bytes) return '-'
  return bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
function formatDuration(s) {
  if (!s) return '-'
  const m = Math.floor(s / 60), sec = s % 60
  return `${m}:${String(sec).padStart(2, '0')}`
}
function formatDurationLong(s) {
  if (!s) return '0 分钟'
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60)
  return h > 0 ? `${h} 小时 ${m} 分钟` : `${m} 分钟`
}
function statusType(s) {
  return { completed: 'success', recording: 'warning', failed: 'danger', synced: 'info' }[s] || ''
}

function cameraLabel(mac) {
  const cam = cameras.value.find((c) => c.device_mac === mac)
  return cam ? cam.onvif_host : mac
}

// daily bar max for scaling
function dailyMax(daily) {
  return Math.max(...(daily || []).map((d) => d.count), 1)
}
</script>

<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">录像库</h2>
      <el-button @click="openStats">录制统计</el-button>
    </div>

    <el-form :inline="true" :model="filter" class="filter-bar">
      <el-form-item label="摄像头">
        <el-select v-model="filter.camera_mac" placeholder="全部" clearable style="width: 200px">
          <el-option v-for="c in cameras" :key="c.device_mac" :label="c.onvif_host" :value="c.device_mac" />
        </el-select>
      </el-form-item>
      <el-form-item label="日期">
        <el-date-picker v-model="filter.date" type="date" value-format="YYYY-MM-DD" placeholder="全部日期" clearable />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="fetchRecordings">查询</el-button>
      </el-form-item>
    </el-form>

    <el-table v-loading="loading" :data="recordings" stripe border style="width: 100%">
      <el-table-column prop="camera_mac" label="摄像头 MAC" min-width="160" />
      <el-table-column label="开始时间" width="170">
        <template #default="{ row }">{{ new Date(row.started_at).toLocaleString('zh-CN') }}</template>
      </el-table-column>
      <el-table-column label="时长" width="90">
        <template #default="{ row }">{{ formatDuration(row.duration) }}</template>
      </el-table-column>
      <el-table-column label="大小" width="100">
        <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240" align="center">
        <template #default="{ row }">
          <el-tooltip
            :content="row.status === 'recording' ? '录制中，暂不可播放' : row.status === 'failed' ? '录制失败，无可用文件' : ''"
            :disabled="row.status !== 'recording' && row.status !== 'failed'"
          >
            <el-button
              size="small"
              type="primary"
              :disabled="row.status === 'recording' || row.status === 'failed'"
              :loading="hlsConvertingId === row.id"
              @click="playRecording(row)"
            >
              {{ hlsConvertingId === row.id ? '转码中' : '播放' }}
            </el-button>
          </el-tooltip>
          <el-button
            size="small"
            :disabled="row.status === 'recording' || row.status === 'failed'"
            style="margin-left: 6px"
            @click="downloadRecording(row)"
          >下载</el-button>
          <el-button size="small" type="danger" style="margin-left: 6px" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="filter.page"
      :page-size="filter.page_size"
      :total="total"
      layout="total, prev, pager, next"
      class="pagination-bar"
      @current-change="fetchRecordings"
    />

    <!-- 播放弹窗 -->
    <el-dialog v-model="playDialog" title="录像回放" width="720px" destroy-on-close @close="closePlay">
      <CameraPlayer :src="playUrl" :mode="playMode" />
    </el-dialog>

    <!-- 统计弹窗 -->
    <el-dialog v-model="statsDialog" title="录制统计" width="680px" destroy-on-close>
      <div class="stats-toolbar">
        <el-radio-group v-model="statsFilter.range" @change="fetchStats">
          <el-radio-button value="7d">近 7 天</el-radio-button>
          <el-radio-button value="30d">近 30 天</el-radio-button>
        </el-radio-group>
        <el-select v-model="statsFilter.camera_mac" clearable placeholder="全部摄像头" style="width:180px" @change="fetchStats">
          <el-option v-for="c in cameras" :key="c.device_mac" :label="c.onvif_host" :value="c.device_mac" />
        </el-select>
      </div>

      <el-skeleton v-if="statsLoading" :rows="4" animated style="margin-top:12px" />

      <template v-if="statsData && !statsLoading">
        <!-- Per-camera summary -->
        <div class="stats-section-title">各摄像头汇总</div>
        <el-table :data="statsData.cameras" size="small" border style="margin-bottom:16px">
          <el-table-column label="摄像头" min-width="140">
            <template #default="{ row }">{{ cameraLabel(row.camera_mac) }}</template>
          </el-table-column>
          <el-table-column prop="count" label="录制次数" width="100" align="right" />
          <el-table-column label="总时长" width="130" align="right">
            <template #default="{ row }">{{ formatDurationLong(row.total_duration_seconds) }}</template>
          </el-table-column>
          <el-table-column label="总大小" width="110" align="right">
            <template #default="{ row }">{{ formatSize(row.total_size_bytes) }}</template>
          </el-table-column>
        </el-table>

        <!-- Daily trend bars -->
        <div class="stats-section-title">每日录制次数</div>
        <div class="daily-chart">
          <div
            v-for="d in statsData.daily"
            :key="d.date"
            class="daily-bar-col"
          >
            <div
              class="daily-bar"
              :style="{ height: Math.max(4, (d.count / dailyMax(statsData.daily)) * 80) + 'px' }"
              :title="`${d.date}: ${d.count} 次 · ${formatDurationLong(d.duration_seconds)}`"
            />
            <div class="daily-label">{{ d.date.slice(5) }}</div>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.filter-bar {
  margin-bottom: 16px;
}

.stats-toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.stats-section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 8px;
}

.daily-chart {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 100px;
  padding-bottom: 20px;
  overflow-x: auto;
}

.daily-bar-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 28px;
  flex: 1;
}

.daily-bar {
  width: 100%;
  background: var(--color-primary, #5e5ce6);
  border-radius: 2px 2px 0 0;
  cursor: default;
  transition: opacity 0.15s;
}

.daily-bar:hover {
  opacity: 0.75;
}

.daily-label {
  font-size: 10px;
  color: var(--color-text-muted);
  margin-top: 4px;
  white-space: nowrap;
}
</style>
