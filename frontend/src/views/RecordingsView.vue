<script setup>
import { ref, onMounted, watch } from 'vue'
import {
  listRecordings, deleteRecording, streamUrl, downloadUrl,
  requestRecordingHls, recordingHlsUrl, getRecordingStats,
} from '@/api/recordings'
import { listCameras } from '@/api/cameras'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoCameraFilled, Clock, FolderOpened } from '@element-plus/icons-vue'
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
const statsFilter = ref({ range: '7d' })
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
    <el-dialog v-model="statsDialog" title="录制统计" width="600px" destroy-on-close>
      <div class="stats-header">
        <el-radio-group v-model="statsFilter.range" @change="fetchStats">
          <el-radio-button value="7d">近 7 天</el-radio-button>
          <el-radio-button value="30d">近 30 天</el-radio-button>
        </el-radio-group>
        <span class="stats-period-hint">{{ statsFilter.range === '7d' ? '过去 7 天的录制汇总' : '过去 30 天的录制汇总' }}</span>
      </div>

      <div v-if="statsLoading" class="stats-skeleton">
        <div v-for="i in 3" :key="i" class="stats-skeleton-tile" />
      </div>

      <template v-else-if="statsData">
        <div class="stats-grid">
          <div class="stat-tile stat-tile--count">
            <div class="stat-icon-wrap">
              <el-icon class="stat-icon"><VideoCameraFilled /></el-icon>
            </div>
            <div class="stat-body">
              <div class="stat-value">{{ statsData.count }}</div>
              <div class="stat-label">录制次数</div>
            </div>
            <div class="stat-glow stat-glow--count" />
          </div>

          <div class="stat-tile stat-tile--duration">
            <div class="stat-icon-wrap">
              <el-icon class="stat-icon"><Clock /></el-icon>
            </div>
            <div class="stat-body">
              <div class="stat-value">{{ formatDurationLong(statsData.total_duration) }}</div>
              <div class="stat-label">总时长</div>
            </div>
            <div class="stat-glow stat-glow--duration" />
          </div>

          <div class="stat-tile stat-tile--size">
            <div class="stat-icon-wrap">
              <el-icon class="stat-icon"><FolderOpened /></el-icon>
            </div>
            <div class="stat-body">
              <div class="stat-value">{{ formatSize(statsData.total_size) }}</div>
              <div class="stat-label">总存储</div>
            </div>
            <div class="stat-glow stat-glow--size" />
          </div>
        </div>

        <div v-if="statsData.count === 0" class="stats-empty">
          该时间段内暂无录制记录
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.filter-bar {
  margin-bottom: 16px;
}

/* ── Stats dialog ─────────────────────────── */
.stats-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
}

.stats-period-hint {
  font-size: 12px;
  color: var(--color-text-muted);
  letter-spacing: 0.01em;
}

/* skeleton */
.stats-skeleton {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.stats-skeleton-tile {
  height: 88px;
  border-radius: var(--radius-md);
  background: linear-gradient(
    90deg,
    var(--color-surface-raised) 25%,
    var(--color-surface-overlay) 37%,
    var(--color-surface-raised) 63%
  );
  background-size: 400% 100%;
  animation: shimmer 1.4s ease infinite;
}

@keyframes shimmer {
  0%   { background-position: 100% 50%; }
  100% { background-position: 0%   50%; }
}

/* grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  animation: stats-in 0.28s var(--easing-snap, cubic-bezier(0.16, 1, 0.3, 1)) both;
}

@keyframes stats-in {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* tile */
.stat-tile {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 16px;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: border-color var(--duration-base) ease,
              background var(--duration-base) ease;
}

.stat-tile::after {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  border-radius: var(--radius-md) 0 0 var(--radius-md);
}

.stat-tile--count::after   { background: var(--color-primary); }
.stat-tile--duration::after { background: var(--color-online, #26C281); }
.stat-tile--size::after    { background: var(--color-warning, #F07D38); }

.stat-tile:hover {
  border-color: var(--color-border-subtle, #28282b);
  background: var(--color-surface-overlay);
}

/* icon badge */
.stat-icon-wrap {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-tile--count   .stat-icon-wrap { background: rgba(94, 92, 230, 0.12); }
.stat-tile--duration .stat-icon-wrap { background: rgba(38, 194, 129, 0.12); }
.stat-tile--size    .stat-icon-wrap { background: rgba(240, 125, 56, 0.12); }

.stat-icon {
  font-size: 18px;
}

.stat-tile--count   .stat-icon { color: var(--color-primary); }
.stat-tile--duration .stat-icon { color: var(--color-online, #26C281); }
.stat-tile--size    .stat-icon { color: var(--color-warning, #F07D38); }

/* text */
.stat-body {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.2;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stat-label {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 4px;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  font-weight: 500;
}

/* ambient glow */
.stat-glow {
  position: absolute;
  right: -20px;
  top: -20px;
  width: 70px;
  height: 70px;
  border-radius: 50%;
  opacity: 0.06;
  pointer-events: none;
}

.stat-glow--count    { background: var(--color-primary); }
.stat-glow--duration { background: var(--color-online, #26C281); }
.stat-glow--size     { background: var(--color-warning, #F07D38); }

/* empty hint */
.stats-empty {
  margin-top: 14px;
  text-align: center;
  font-size: 12px;
  color: var(--color-text-muted);
  padding: 12px 0 4px;
}
</style>
