<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  listRecordings,
  deleteRecording,
  streamUrl,
  downloadUrl,
  getRecordingStats,
  openRecordingFolder,
} from '@/api/recordings'
import { listCameras } from '@/api/cameras'
import { listDevices } from '@/api/devices'
import {
  VideoCameraFilled,
  Clock,
  FolderOpened,
  VideoPlay,
  Download,
  Delete,
  MoreFilled,
  RefreshLeft,
} from '@element-plus/icons-vue'
import CameraPlayer from '@/components/CameraPlayer.vue'
import EmptyState from '@/components/EmptyState.vue'
import StatCard from '@/components/StatCard.vue'
import { useNotificationsStore } from '@/stores/notifications'
import { useI18n } from 'vue-i18n'
import { useFormatDuration } from '@/composables/useFormatDuration'
import { useApiError } from '@/composables/useApiError'
import { scheduleUndo } from '@/composables/useUndo'

const { t, d: formatDate } = useI18n()
const router = useRouter()
const { formatDurationLong } = useFormatDuration()
const handleError = useApiError()

const recordings = ref([])
const total = ref(0)
const loading = ref(false)
const cameras = ref([])
const deviceByMac = ref({})
const notifications = useNotificationsStore()

const filter = ref({ camera_mac: '', date: '', page: 1, page_size: 20 })

const headerStats = ref(null)
const headerStatsLoading = ref(false)

async function loadDeviceMap() {
  const map = {}
  let page = 1
  const page_size = 200
  while (true) {
    const { data } = await listDevices({ page, page_size })
    for (const dev of data.items || []) {
      map[dev.mac] = dev
    }
    if (page >= data.pages) break
    page += 1
  }
  return map
}

onMounted(async () => {
  const [camRes, deviceMap] = await Promise.all([listCameras(), loadDeviceMap()])
  cameras.value = camRes.data
  deviceByMac.value = deviceMap
  await Promise.all([fetchRecordings(), fetchHeaderStats()])
})

watch(
  () => notifications.lastRecordingEvent,
  () => {
    fetchRecordings()
    fetchHeaderStats()
  },
)

watch(
  () => [filter.value.camera_mac, filter.value.date],
  () => {
    filter.value.page = 1
    fetchRecordings()
    fetchHeaderStats()
  },
)

watch(
  () => filter.value.page_size,
  () => {
    filter.value.page = 1
    fetchRecordings()
  },
)

const hasActiveFilters = computed(() => Boolean(filter.value.camera_mac || filter.value.date))

const cameraByMac = computed(() => {
  const map = {}
  for (const c of cameras.value) {
    map[c.device_mac] = c
  }
  return map
})

function cameraDisplayName(mac) {
  const dev = deviceByMac.value[mac]
  const cam = cameraByMac.value[mac]
  return dev?.alias || dev?.hostname || cam?.onvif_host || mac
}

function cameraSelectLabel(cam) {
  const dev = deviceByMac.value[cam.device_mac]
  const name = dev?.alias || dev?.hostname || cam.onvif_host
  return `${name} (${cam.device_mac})`
}

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

function buildStatsParams(range = '7d') {
  const params = { range }
  if (filter.value.camera_mac) params.camera_mac = filter.value.camera_mac
  if (filter.value.date) params.date = filter.value.date
  return params
}

const headerStatsDescription = computed(() =>
  hasActiveFilters.value ? t('recordings.statsHintFiltered') : t('recordings.statsHint7d'),
)

async function fetchHeaderStats() {
  headerStatsLoading.value = true
  try {
    const { data } = await getRecordingStats(buildStatsParams('7d'))
    headerStats.value = data
  } catch {
    headerStats.value = null
  } finally {
    headerStatsLoading.value = false
  }
}

function resetFilters() {
  filter.value.camera_mac = ''
  filter.value.date = ''
}

// ── Playback ─────────────────────────────────────────────────
const playDialog = ref(false)
const playUrl = ref('')
const playMode = ref('recorded')
const playingRecording = ref(null)

function isPlayable(row) {
  return row.status !== 'recording' && row.status !== 'failed'
}

function playRecording(rec) {
  if (!isPlayable(rec)) return
  playingRecording.value = rec
  playUrl.value = streamUrl(rec.id)
  playMode.value = 'recorded'
  playDialog.value = true
}

function closePlay() {
  playUrl.value = ''
  playingRecording.value = null
}

function handleRowClick(row) {
  playRecording(row)
}

function rowClassName({ row }) {
  return isPlayable(row) ? 'row-playable' : ''
}

const playDialogTitle = computed(() => {
  const rec = playingRecording.value
  if (!rec) return t('recordings.playback')
  return t('recordings.playbackTitle', {
    camera: cameraDisplayName(rec.camera_mac),
    time: formatDate(new Date(rec.started_at), 'short'),
  })
})

async function openFolder(row) {
  if (row.storage_type === 'nas' && row.nas_access_url) {
    window.open(row.nas_access_url)
    return
  }
  if (row.storage_type === 'local') {
    try {
      await openRecordingFolder(row.id)
    } catch (e) {
      handleError(e, 'recordings.openFolderFailed')
    }
  }
}

async function handleDelete(rec) {
  const originalIndex = recordings.value.findIndex((r) => r.id === rec.id)
  if (originalIndex === -1) return
  recordings.value.splice(originalIndex, 1)
  total.value = Math.max(0, total.value - 1)
  scheduleUndo({
    label: t('recordings.deleted'),
    performDelete: async () => {
      await deleteRecording(rec.id)
      await fetchHeaderStats()
    },
    onUndo: () => {
      recordings.value.splice(originalIndex, 0, rec)
      total.value += 1
      fetchHeaderStats()
    },
    onError: (e) => handleError(e, 'recordings.deleteFailed'),
  })
}

function downloadRecording(rec) {
  const token = localStorage.getItem('token')
  const url = downloadUrl(rec.id) + `?token=${token}`
  const a = document.createElement('a')
  a.href = url
  a.download = rec.file_name || `recording_${rec.id}.mp4`
  a.click()
}

function handleMoreCommand(cmd, row) {
  if (cmd === 'download') downloadRecording(row)
  else if (cmd === 'folder') openFolder(row)
  else if (cmd === 'delete') handleDelete(row)
}

function goToCameras() {
  router.push('/cameras')
}

// ── Stats dialog ─────────────────────────────────────────────
const statsDialog = ref(false)
const statsFilter = ref({ range: '7d' })
const statsData = ref(null)
const statsLoading = ref(false)

async function openStats() {
  statsDialog.value = true
  statsFilter.value.range = '7d'
  await fetchStats()
}

async function fetchStats() {
  statsLoading.value = true
  statsData.value = null
  try {
    const { data } = await getRecordingStats(buildStatsParams(statsFilter.value.range))
    statsData.value = data
  } catch (e) {
    handleError(e, 'recordings.statsFailed')
  } finally {
    statsLoading.value = false
  }
}

function formatSize(bytes) {
  if (!bytes) return '-'
  if (bytes < 1024) return t('charts.size.bytes', { n: bytes })
  if (bytes < 1024 * 1024) return t('charts.size.kb', { n: (bytes / 1024).toFixed(1) })
  if (bytes < 1024 * 1024 * 1024)
    return t('charts.size.mb', { n: (bytes / 1024 / 1024).toFixed(1) })
  if (bytes < 1024 * 1024 * 1024 * 1024)
    return t('charts.size.gb', { n: (bytes / 1024 / 1024 / 1024).toFixed(1) })
  return t('charts.size.tb', { n: (bytes / 1024 / 1024 / 1024 / 1024).toFixed(1) })
}

function formatDuration(s) {
  if (!s) return '-'
  const m = Math.floor(s / 60)
  const sec = s % 60
  return t('charts.duration.short', { m, s: String(sec).padStart(2, '0') })
}

function formatRelativeTime(iso) {
  const then = new Date(iso).getTime()
  const diffMin = Math.floor((Date.now() - then) / 60000)
  if (diffMin < 1) return t('recordings.relativeJustNow')
  if (diffMin < 60) return t('recordings.relativeMinutes', { n: diffMin })
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return t('recordings.relativeHours', { n: diffHr })
  const diffDay = Math.floor(diffHr / 24)
  return t('recordings.relativeDays', { n: diffDay })
}

function statusType(s) {
  return { completed: 'success', recording: 'warning', failed: 'danger', synced: 'info' }[s] || ''
}

const statusLabels = {
  completed: 'recordings.statusCompleted',
  recording: 'recordings.statusRecording',
  failed: 'recordings.statusFailed',
  synced: 'recordings.statusSynced',
}

function statusLabel(s) {
  return t(statusLabels[s] || s)
}

function showStatusBadge(status) {
  return status && status !== 'completed'
}

function segmentLabel(row) {
  if (row.segment_index == null) return ''
  return t('recordings.segment', { n: row.segment_index + 1 })
}

function storageLabel(row) {
  return row.storage_type === 'nas' ? t('recordings.storageNas') : t('recordings.storageLocal')
}
</script>

<template>
  <div>
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ $t('recordings.title') }}</h2>
        <span class="page-sub">{{ $t('recordings.pageSummary', { total }) }}</span>
      </div>
      <div class="header-actions">
        <el-button @click="openStats">{{ $t('recordings.recordingStats') }}</el-button>
      </div>
    </div>

    <div v-if="headerStatsLoading && !headerStats" class="stats-grid">
      <el-skeleton v-for="i in 3" :key="i" :rows="2" animated class="stats-skeleton-card" />
    </div>
    <div v-else-if="headerStats" class="stats-grid">
      <StatCard
        :title="$t('recordings.count')"
        :value="headerStats.count"
        :description="headerStatsDescription"
        variant="recordings"
      >
        <template #icon>
          <el-icon><VideoCameraFilled /></el-icon>
        </template>
      </StatCard>
      <StatCard
        :title="$t('recordings.totalDuration')"
        :value="formatDurationLong(headerStats.total_duration)"
        :description="headerStatsDescription"
        variant="recordings"
      >
        <template #icon>
          <el-icon><Clock /></el-icon>
        </template>
      </StatCard>
      <StatCard
        :title="$t('recordings.totalSize')"
        :value="formatSize(headerStats.total_size)"
        :description="headerStatsDescription"
        variant="recordings"
      >
        <template #icon>
          <el-icon><FolderOpened /></el-icon>
        </template>
      </StatCard>
    </div>

    <div class="filter-section">
      <div class="filter-row">
        <el-select
          v-model="filter.camera_mac"
          :placeholder="$t('recordings.all')"
          clearable
          class="filter-camera"
        >
          <el-option
            v-for="c in cameras"
            :key="c.device_mac"
            :label="cameraSelectLabel(c)"
            :value="c.device_mac"
          />
        </el-select>

        <el-date-picker
          v-model="filter.date"
          type="date"
          value-format="YYYY-MM-DD"
          :placeholder="$t('recordings.allDates')"
          clearable
        />

        <el-button v-if="hasActiveFilters" :icon="RefreshLeft" @click="resetFilters">
          {{ $t('recordings.resetFilters') }}
        </el-button>

        <span class="filter-result">{{ $t('recordings.filterResult', { n: total }) }}</span>
      </div>

      <div v-if="hasActiveFilters" class="filter-tags">
        <el-tag v-if="filter.camera_mac" closable size="small" @close="filter.camera_mac = ''">
          {{ cameraDisplayName(filter.camera_mac) }}
        </el-tag>
        <el-tag v-if="filter.date" closable size="small" @close="filter.date = ''">
          {{ filter.date }}
        </el-tag>
      </div>
    </div>

    <div class="table-card glass-card">
      <div class="table-scroll">
        <el-table
          v-loading="loading"
          :data="recordings"
          :row-class-name="rowClassName"
          style="width: 100%"
          @row-click="handleRowClick"
        >
          <template #empty>
            <EmptyState
              icon="recording"
              :title="$t('common.empty.recordings.title')"
              :description="$t('common.empty.recordings.description')"
              :action-label="$t('recordings.goToCameras')"
              @action="goToCameras"
            />
          </template>

          <el-table-column
            v-if="!filter.camera_mac"
            :label="$t('recordings.cameraMac')"
            min-width="160"
          >
            <template #default="{ row }">
              <div class="camera-cell">
                <span class="camera-name">{{ cameraDisplayName(row.camera_mac) }}</span>
                <span class="camera-mac">{{ row.camera_mac }}</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column :label="$t('recordings.startTime')" min-width="180">
            <template #default="{ row }">
              <el-tooltip
                :content="formatDate(new Date(row.started_at), 'short')"
                placement="top"
                :show-after="400"
              >
                <div class="time-cell">
                  <div class="time-primary">
                    <span class="time-relative">{{ formatRelativeTime(row.started_at) }}</span>
                    <el-tag
                      v-if="showStatusBadge(row.status)"
                      :type="statusType(row.status)"
                      size="small"
                      class="time-status"
                    >
                      {{ statusLabel(row.status) }}
                    </el-tag>
                  </div>
                  <span v-if="segmentLabel(row)" class="time-segment">{{ segmentLabel(row) }}</span>
                </div>
              </el-tooltip>
            </template>
          </el-table-column>

          <el-table-column :label="$t('recordings.duration')" width="90" align="right">
            <template #default="{ row }">
              <span class="tabular-nums">{{ formatDuration(row.duration) }}</span>
            </template>
          </el-table-column>

          <el-table-column :label="$t('recordings.size')" width="100" align="right">
            <template #default="{ row }">
              <span class="tabular-nums">{{ formatSize(row.file_size) }}</span>
            </template>
          </el-table-column>

          <el-table-column :label="$t('recordings.storage')" width="90">
            <template #default="{ row }">
              <button
                type="button"
                class="storage-link"
                :title="
                  row.storage_type === 'local'
                    ? $t('recordings.openLocalFolder')
                    : $t('recordings.openNasFolder')
                "
                @click.stop="openFolder(row)"
              >
                <el-icon aria-hidden="true"><FolderOpened /></el-icon>
                {{ storageLabel(row) }}
              </button>
            </template>
          </el-table-column>

          <el-table-column
            :label="$t('recordings.actions')"
            width="150"
            align="center"
            class-name="action-cell"
            label-class-name="action-cell"
          >
            <template #default="{ row }">
              <div class="action-group" @click.stop>
                <el-button
                  class="play-btn"
                  type="primary"
                  link
                  :icon="VideoPlay"
                  :disabled="!isPlayable(row)"
                  @click="playRecording(row)"
                >
                  {{ $t('recordings.play') }}
                </el-button>

                <el-dropdown trigger="click" @command="(cmd) => handleMoreCommand(cmd, row)">
                  <el-button
                    class="action-btn"
                    size="small"
                    :icon="MoreFilled"
                    :aria-label="$t('recordings.moreActions')"
                  />
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="download" :disabled="!isPlayable(row)">
                        <el-icon><Download /></el-icon>
                        {{ $t('recordings.download') }}
                      </el-dropdown-item>
                      <el-dropdown-item command="folder">
                        <el-icon><FolderOpened /></el-icon>
                        {{
                          row.storage_type === 'local'
                            ? $t('recordings.openLocalFolder')
                            : $t('recordings.openNasFolder')
                        }}
                      </el-dropdown-item>
                      <el-dropdown-item command="delete" divided>
                        <el-icon class="danger-icon"><Delete /></el-icon>
                        {{ $t('common.delete') }}
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div v-if="total > 0" class="table-footer">
        <el-pagination
          v-model:current-page="filter.page"
          v-model:page-size="filter.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="fetchRecordings"
          @size-change="fetchRecordings"
        />
      </div>
    </div>

    <el-dialog
      v-model="playDialog"
      :title="playDialogTitle"
      width="720px"
      destroy-on-close
      @close="closePlay"
    >
      <CameraPlayer :src="playUrl" :mode="playMode" />
      <template v-if="playingRecording" #footer>
        <el-button :icon="FolderOpened" @click="openFolder(playingRecording)">
          {{
            playingRecording.storage_type === 'local'
              ? $t('recordings.openLocalFolder')
              : $t('recordings.openNasFolder')
          }}
        </el-button>
        <el-button
          :icon="Download"
          :disabled="!isPlayable(playingRecording)"
          @click="downloadRecording(playingRecording)"
        >
          {{ $t('recordings.download') }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="statsDialog"
      :title="$t('recordings.statsTitle')"
      width="600px"
      destroy-on-close
    >
      <div class="stats-header">
        <el-radio-group v-model="statsFilter.range" @change="fetchStats">
          <el-radio-button value="7d">{{ $t('recordings.statsRange7d') }}</el-radio-button>
          <el-radio-button value="30d">{{ $t('recordings.statsRange30d') }}</el-radio-button>
        </el-radio-group>
        <span class="stats-period-hint">{{
          statsFilter.range === '7d' ? $t('recordings.statsHint7d') : $t('recordings.statsHint30d')
        }}</span>
      </div>

      <div v-if="statsLoading" class="stats-dialog-skeleton">
        <el-skeleton :rows="1" animated class="stats-skeleton-inner" />
      </div>

      <template v-else-if="statsData">
        <div class="stats-dialog-grid">
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
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.stats-skeleton-card {
  padding: var(--space-5);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.filter-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.filter-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.filter-camera {
  width: 240px;
}

.filter-result {
  margin-left: auto;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.filter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.table-card {
  overflow: hidden;
  min-width: 0;
}

.table-scroll {
  overflow-x: auto;
  overflow-y: hidden;
  min-width: 0;
}

.table-footer {
  display: flex;
  justify-content: flex-end;
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--color-border-subtle);
}

.camera-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.camera-name {
  font-size: 13px;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.camera-mac {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-muted);
}

.time-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.time-primary {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.time-relative {
  font-size: 13px;
  color: var(--color-text-primary);
}

.time-status {
  flex-shrink: 0;
}

.time-segment {
  font-size: 11px;
  color: var(--color-text-muted);
}

.storage-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0;
  border: none;
  background: none;
  font-size: 12px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: color var(--duration-fast) ease;
}

.storage-link:hover {
  color: var(--color-primary);
}

.action-group {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.play-btn {
  font-size: 13px;
  font-weight: 500;
}

.action-btn {
  --el-button-bg-color: transparent;
  --el-button-border-color: transparent;
  --el-button-hover-bg-color: var(--color-surface-raised);
  height: 28px;
  width: 28px;
  padding: 3px;
}

.danger-icon {
  color: var(--color-error);
}

:deep(.row-playable) {
  cursor: pointer;
}

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
  padding: 12px 0;
}

:deep(.el-table__body td.el-table__cell) {
  padding: 12px 0;
}

:deep(.el-table__body td.action-cell.el-table__cell),
:deep(.el-table__header th.action-cell.el-table__cell) {
  overflow: visible;
}

:deep(td.action-cell .cell),
:deep(th.action-cell .cell) {
  overflow: visible;
}

:deep(.el-table__inner-wrapper::before) {
  display: none;
}

:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 13px;
}

/* Stats dialog */
.stats-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.stats-period-hint {
  font-size: 12px;
  color: var(--color-text-muted);
}

.stats-dialog-skeleton {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.stats-skeleton-inner :deep(.el-skeleton__item) {
  height: 88px;
  border-radius: var(--radius-md);
}

.stats-dialog-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

@media (max-width: 1023.98px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767.98px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .filter-result {
    margin-left: 0;
    width: 100%;
  }

  .stats-dialog-grid,
  .stats-dialog-skeleton {
    grid-template-columns: 1fr;
  }

  .table-footer {
    justify-content: center;
  }

  .table-footer :deep(.el-pagination) {
    flex-wrap: wrap;
    justify-content: center;
    row-gap: var(--space-2);
  }
}

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

.stat-tile--count::after {
  background: var(--color-primary);
}
.stat-tile--duration::after {
  background: var(--color-online);
}
.stat-tile--size::after {
  background: var(--color-warning);
}

.stat-icon-wrap {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary-subtle);
}

.stat-tile--count .stat-icon {
  color: var(--color-primary);
}
.stat-tile--duration .stat-icon {
  color: var(--color-online);
}
.stat-tile--size .stat-icon {
  color: var(--color-warning);
}

.stat-icon {
  font-size: 18px;
}

.stat-body {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.2;
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
}

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

.stat-glow--count {
  background: var(--color-primary);
}
.stat-glow--duration {
  background: var(--color-online);
}
.stat-glow--size {
  background: var(--color-warning);
}

.stats-empty {
  margin-top: 14px;
  text-align: center;
  font-size: 12px;
  color: var(--color-text-muted);
  padding: 12px 0 4px;
}
</style>
