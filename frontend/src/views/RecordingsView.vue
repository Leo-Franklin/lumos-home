<script setup>
import { ref, onMounted, watch } from 'vue'
import {
  listRecordings, deleteRecording, streamUrl, downloadUrl,
  requestRecordingHls, recordingHlsUrl, getRecordingStats,
} from '@/api/recordings'
import { listCameras } from '@/api/cameras'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoCameraFilled, Clock, FolderOpened, VideoPlay, Download, Delete } from '@element-plus/icons-vue'
import CameraPlayer from '@/components/CameraPlayer.vue'
import { useNotificationsStore } from '@/stores/notifications'
import { useI18n } from 'vue-i18n'
import { useFormatDuration } from '@/composables/useFormatDuration'

const { t } = useI18n()
const { formatDurationLong } = useFormatDuration()

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
      ElMessage.info(t('recordings.transcoding'))
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
        ElMessage.success(t('recordings.transcodeComplete'))
        playUrl.value = recordingHlsUrl(rec.id)
        playMode.value = 'hls'
        playDialog.value = true
      }
    } catch (e) {
      if (e.response?.status !== 202) {
        clearInterval(hlsPollTimer)
        hlsPollTimer = null
        hlsConvertingId.value = null
        ElMessage.error(t('recordings.transcodeFailed'))
      }
    }
  }, 3000)
}

function closePlay() {
  playUrl.value = ''
}

async function handleDelete(rec) {
  try {
    await ElMessageBox.confirm(t('recordings.deleteConfirm'), t('common.confirmDelete'), { type: 'warning' })
  } catch { return }
  try {
    await deleteRecording(rec.id)
    ElMessage.success(t('recordings.deleted'))
    fetchRecordings()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || t('recordings.deleteFailed'))
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
    ElMessage.error(e.response?.data?.detail || t('recordings.statsFailed'))
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
function statusType(s) {
  return { completed: 'success', recording: 'warning', failed: 'danger', synced: 'info' }[s] || ''
}
const statusLabels = { completed: 'recordings.statusCompleted', recording: 'recordings.statusRecording', failed: 'recordings.statusFailed', synced: 'recordings.statusSynced' }
function statusLabel(s) {
  return t(statusLabels[s] || s)
}

function cameraLabel(mac) {
  const cam = cameras.value.find((c) => c.device_mac === mac)
  return cam ? cam.onvif_host : mac
}
</script>

<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">{{ $t('recordings.title') }}</h2>
      <el-button @click="openStats">{{ $t('recordings.recordingStats') }}</el-button>
    </div>

    <el-form :inline="true" :model="filter" class="filter-bar">
      <el-form-item :label="$t('recordings.camera')">
        <el-select v-model="filter.camera_mac" :placeholder="$t('recordings.all')" clearable style="width: 200px">
          <el-option v-for="c in cameras" :key="c.device_mac" :label="c.onvif_host" :value="c.device_mac" />
        </el-select>
      </el-form-item>
      <el-form-item :label="$t('recordings.date')">
        <el-date-picker v-model="filter.date" type="date" value-format="YYYY-MM-DD" :placeholder="$t('recordings.allDates')" clearable />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="fetchRecordings">{{ $t('recordings.query') }}</el-button>
      </el-form-item>
    </el-form>

    <el-table v-loading="loading" :data="recordings" style="width: 100%">
      <el-table-column prop="camera_mac" :label="$t('recordings.cameraMac')" min-width="160" />
      <el-table-column :label="$t('recordings.startTime')" width="170">
        <template #default="{ row }">{{ new Date(row.started_at).toLocaleString('zh-CN') }}</template>
      </el-table-column>
      <el-table-column :label="$t('recordings.duration')" width="90">
        <template #default="{ row }">{{ formatDuration(row.duration) }}</template>
      </el-table-column>
      <el-table-column :label="$t('recordings.size')" width="100">
        <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
      </el-table-column>
      <el-table-column :label="$t('recordings.status')" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('recordings.actions')" width="180" align="center">
        <template #default="{ row }">
          <div class="action-group">
            <el-tooltip
              :content="row.status === 'recording' ? t('recordings.recordingActive') : row.status === 'failed' ? t('recordings.recordingFailed') : t('recordings.play')"
              :disabled="row.status !== 'recording' && row.status !== 'failed'"
            >
              <el-button
                class="action-btn action-btn--primary"
                size="small"
                :icon="VideoPlay"
                :disabled="row.status === 'recording' || row.status === 'failed'"
                :loading="hlsConvertingId === row.id"
                @click="playRecording(row)"
              />
            </el-tooltip>
            <el-tooltip
              :content="$t('recordings.download')"
              :disabled="row.status !== 'recording' && row.status !== 'failed'"
            >
              <el-button
                class="action-btn"
                size="small"
                :icon="Download"
                :disabled="row.status === 'recording' || row.status === 'failed'"
                @click="downloadRecording(row)"
              />
            </el-tooltip>
            <el-tooltip :content="$t('common.delete')" :show-after="400">
              <el-button class="action-btn action-btn--danger" size="small" :icon="Delete" @click="handleDelete(row)" />
            </el-tooltip>
          </div>
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
    <el-dialog v-model="playDialog" :title="$t('recordings.playback')" width="720px" destroy-on-close @close="closePlay">
      <CameraPlayer :src="playUrl" :mode="playMode" />
    </el-dialog>

    <!-- 统计弹窗 -->
    <el-dialog v-model="statsDialog" :title="$t('recordings.statsTitle')" width="600px" destroy-on-close>
      <div class="stats-header">
        <el-radio-group v-model="statsFilter.range" @change="fetchStats">
          <el-radio-button value="7d">{{ $t('recordings.statsRange7d') }}</el-radio-button>
          <el-radio-button value="30d">{{ $t('recordings.statsRange30d') }}</el-radio-button>
        </el-radio-group>
        <span class="stats-period-hint">{{ statsFilter.range === '7d' ? $t('recordings.statsHint7d') : $t('recordings.statsHint30d') }}</span>
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
              <div class="stat-label">{{ $t('recordings.count') }}</div>
            </div>
            <div class="stat-glow stat-glow--count" />
          </div>

          <div class="stat-tile stat-tile--duration">
            <div class="stat-icon-wrap">
              <el-icon class="stat-icon"><Clock /></el-icon>
            </div>
            <div class="stat-body">
              <div class="stat-value">{{ formatDurationLong(statsData.total_duration) }}</div>
              <div class="stat-label">{{ $t('recordings.totalDuration') }}</div>
            </div>
            <div class="stat-glow stat-glow--duration" />
          </div>

          <div class="stat-tile stat-tile--size">
            <div class="stat-icon-wrap">
              <el-icon class="stat-icon"><FolderOpened /></el-icon>
            </div>
            <div class="stat-body">
              <div class="stat-value">{{ formatSize(statsData.total_size) }}</div>
              <div class="stat-label">{{ $t('recordings.totalSize') }}</div>
            </div>
            <div class="stat-glow stat-glow--size" />
          </div>
        </div>

        <div v-if="statsData.count === 0" class="stats-empty">
          {{ $t('recordings.noRecordings') }}
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

/* ── Table styling ──────────────────────────── */
:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-header-text-color: var(--color-text-muted);
  --el-table-border-color: var(--color-border-subtle);
  --el-table-row-hover-bg-color: var(--color-surface-raised);
  background: transparent;
}

:deep(.el-table__header th.el-table__cell) {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 10px 0;
}

:deep(.el-table__body td.el-table__cell) {
  padding: 10px 0;
}

:deep(.el-table__inner-wrapper::before) {
  display: none;
}

/* Action buttons */
.action-group {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1px;
}

.action-btn {
  --el-button-bg-color: transparent;
  --el-button-border-color: transparent;
  --el-button-hover-bg-color: var(--color-surface-raised);
  --el-button-hover-border-color: transparent;
  --el-button-hover-text-color: var(--color-text-primary);
  --el-button-active-bg-color: var(--color-surface-overlay);
  --el-button-active-border-color: transparent;
  height: 28px;
  width: 28px;
  padding: 3px;
  border-radius: 5px;
  font-size: 15px;
  transition: background var(--duration-fast) ease-out,
              color var(--duration-fast) ease-out;
}

.action-btn--primary {
  --el-button-hover-bg-color: rgba(94, 92, 230, 0.1);
  --el-button-hover-text-color: var(--color-primary);
  --el-button-active-bg-color: rgba(94, 92, 230, 0.15);
}

.action-btn--danger {
  --el-button-hover-bg-color: rgba(240, 82, 82, 0.1);
  --el-button-hover-text-color: var(--color-error);
  --el-button-active-bg-color: rgba(240, 82, 82, 0.15);
}
</style>
