<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { getDashboard } from '@/api/system'
import { Refresh } from '@element-plus/icons-vue'
import { useFormatDuration } from '@/composables/useFormatDuration'
import { useNotificationsStore } from '@/stores/notifications'

const { t } = useI18n()
const { formatDuration } = useFormatDuration()
const notifications = useNotificationsStore()

const data = ref(null)
const loading = ref(false)
const error = ref('')

const EVENT_CATEGORY = {
  device_online:           'device',
  device_offline:          'device',
  unknown_device_detected: 'device',
  camera_online:           'camera',
  camera_offline:          'camera',
  recording_started:       'camera',
  recording_completed:     'camera',
  recording_failed:        'camera',
  member_arrived:          'member',
  member_left:             'member',
  scan_completed:          'system',
  dlna_discover_completed: 'system',
  dlna_cast_started:       'system',
}

function eventLabel(msg) {
  const d = msg.data || {}
  switch (msg.event) {
    case 'device_online':          return t('dashboard.event_device_online',          d)
    case 'device_offline':         return t('dashboard.event_device_offline',         d)
    case 'unknown_device_detected':return t('dashboard.event_unknown_device',        d)
    case 'camera_online':          return t('dashboard.event_camera_online',         d)
    case 'camera_offline':         return t('dashboard.event_camera_offline',        d)
    case 'recording_started':      return t('dashboard.event_recording_started',     d)
    case 'recording_completed':    return t('dashboard.event_recording_completed',   d)
    case 'recording_failed':       return t('dashboard.event_recording_failed',      d)
    case 'member_arrived':         return t('dashboard.event_member_arrived',        d)
    case 'member_left':            return t('dashboard.event_member_left',           d)
    case 'scan_completed':         return t('dashboard.event_scan_completed')
    case 'dlna_discover_completed':return t('dashboard.event_dlna_discover')
    case 'dlna_cast_started':      return t('dashboard.event_dlna_cast')
    default:                       return msg.event
  }
}

const recentEvents = computed(() =>
  notifications.messages.slice(0, 20).map((msg) => ({
    category: EVENT_CATEGORY[msg.event] || 'system',
    label: eventLabel(msg),
  }))
)

let timer = null

async function fetchDashboard() {
  loading.value = true
  error.value = ''
  try {
    const { data: d } = await getDashboard()
    data.value = d
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || t('dashboard.loadFailed')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchDashboard()
  timer = setInterval(fetchDashboard, 30000)
})

onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">{{ $t('dashboard.title') }}</h2>
      <el-button :icon="Refresh" :loading="loading" @click="fetchDashboard">{{ $t('common.refresh') }}</el-button>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon style="margin-bottom: 16px" />
    <el-skeleton v-if="!data && loading" :rows="4" animated />

    <template v-if="data">
      <div class="stats-grid">

        <div class="stat-card stat-card--members">
          <div class="stat-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="9" cy="7" r="4"/><path d="M3 21v-2a7 7 0 0 1 10-5.5"/><circle cx="17" cy="8" r="3"/><path d="M14 21v-2a5 5 0 0 1 3.5-4.8"/></svg></div>
          <div class="stat-body">
            <div class="stat-header">{{ $t('dashboard.membersHome') }}</div>
            <div class="stat-value">
              {{ data.members_home }}<span class="stat-of"> / {{ data.members_total }}</span>
            </div>
            <div class="stat-desc">{{ $t('dashboard.membersHomeDesc') }}</div>
          </div>
        </div>

        <div class="stat-card stat-card--cameras">
          <div class="stat-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M2 8.5A2.5 2.5 0 0 1 4.5 6h9A2.5 2.5 0 0 1 16 8.5v7a2.5 2.5 0 0 1-2.5 2.5h-9A2.5 2.5 0 0 1 2 15.5v-7Z"/><path d="m17 10 4.5-3v10L17 14"/><circle cx="7" cy="12" r="1.5" fill="currentColor" stroke="none" :class="{ 'recording-dot': data.cameras_recording > 0 }"/></svg></div>
          <div class="stat-body">
            <div class="stat-header">{{ $t('dashboard.cameras') }}</div>
            <div class="stat-value">
              {{ data.cameras_online }}<span class="stat-of"> / {{ data.cameras_total }}</span>
            </div>
            <div class="stat-desc">
              {{ $t('dashboard.camerasOnline') }}
              <span v-if="data.cameras_recording > 0" class="tag-recording">
                · {{ data.cameras_recording }}{{ $t('dashboard.camerasRecording') }}
              </span>
            </div>
          </div>
        </div>

        <div class="stat-card stat-card--devices">
          <div class="stat-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="2" y="3" width="20" height="12" rx="2"/><path d="M8 21h8"/><path d="M12 15v6"/></svg></div>
          <div class="stat-body">
            <div class="stat-header">{{ $t('dashboard.networkDevices') }}</div>
            <div class="stat-value">
              {{ data.devices_online }}<span class="stat-of"> / {{ data.devices_total }}</span>
            </div>
            <div class="stat-desc">{{ $t('dashboard.devicesOnline') }}</div>
          </div>
        </div>

        <div class="stat-card stat-card--recordings">
          <div class="stat-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8" fill="currentColor" stroke="none" opacity=".85"/></svg></div>
          <div class="stat-body">
            <div class="stat-header">{{ $t('dashboard.todayRecordings') }}</div>
            <div class="stat-value">{{ data.recordings_today_count }}</div>
            <div class="stat-desc">{{ $t('common.unit_record') }} · {{ formatDuration(data.recordings_today_duration_seconds) }}</div>
          </div>
        </div>

        <div class="stat-card stat-card--unknown" :class="{ 'stat-card--warn': data.unknown_devices_today > 0 }">
          <div class="stat-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><circle cx="12" cy="8" r=".5" fill="currentColor"/></svg></div>
          <div class="stat-body">
            <div class="stat-header">{{ $t('dashboard.unknownDevices') }}</div>
            <div class="stat-value">{{ data.unknown_devices_today }}</div>
            <div class="stat-desc">{{ $t('dashboard.todayAppeared') }}</div>
          </div>
        </div>

      </div>

      <div class="activity-panel">
        <div class="activity-header">{{ $t('dashboard.recentActivity') }}</div>
        <div v-if="recentEvents.length" class="activity-list">
          <div
            v-for="(ev, i) in recentEvents"
            :key="i"
            class="activity-item"
            :class="'activity-item--' + ev.category"
          >
            <span class="activity-dot"></span>
            <span class="activity-label">{{ ev.label }}</span>
          </div>
        </div>
        <div v-else class="activity-empty">{{ $t('dashboard.noRecentActivity') }}</div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}

.stat-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 20px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.stat-card--warn {
  border-color: rgba(230, 162, 60, 0.5);
  background: rgba(230, 162, 60, 0.06);
}

.stat-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm, 8px);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  background: var(--color-surface-raised);
}

.stat-icon svg {
  width: 22px;
  height: 22px;
}

.stat-card--members .stat-icon { color: #5E5CE6; background: rgba(94,92,230,.1); }
.stat-card--cameras .stat-icon { color: #34C759; background: rgba(52,199,89,.1); }
.stat-card--devices .stat-icon { color: #007AFF; background: rgba(0,122,255,.1); }
.stat-card--recordings .stat-icon { color: #FF9500; background: rgba(255,149,0,.1); }
.stat-card--unknown .stat-icon { color: #8B8B96; }
.stat-card--warn .stat-icon { color: #E6A23C; background: rgba(230,162,60,.15); }

.stat-body {
  min-width: 0;
}

.stat-header {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1;
  margin-bottom: 6px;
}

.stat-of {
  font-size: 18px;
  font-weight: 400;
  color: var(--color-text-muted);
}

.stat-desc {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.tag-recording {
  color: var(--color-danger, #f05252);
  font-weight: 600;
}

.recording-dot {
  color: #f05252;
}

/* ---- Activity Feed ---- */

.activity-panel {
  margin-top: 20px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 18px 20px;
  max-height: 420px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.activity-header {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.activity-list {
  overflow-y: auto;
  flex: 1;
}

.activity-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 0;
  font-size: 13px;
  color: var(--color-text-primary);
}

.activity-item + .activity-item {
  border-top: 1px solid rgba(128,128,128,.08);
}

.activity-dot {
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-text-muted);
}

.activity-item--device  .activity-dot { background: #007AFF; }
.activity-item--camera  .activity-dot { background: #34C759; }
.activity-item--member  .activity-dot { background: #5E5CE6; }
.activity-item--system  .activity-dot { background: #8B8B96; }

.activity-label {
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  font-size: 13px;
  padding: 32px 0;
}
</style>
