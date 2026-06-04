<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getDashboard } from '@/api/system'
import { Refresh } from '@element-plus/icons-vue'
import { useFormatDuration } from '@/composables/useFormatDuration'
import { useNotificationsStore } from '@/stores/notifications'
import { useConnectionStatus } from '@/composables/useConnectionStatus'
import StatCard from '@/components/StatCard.vue'
import ActivityFeed from '@/components/ActivityFeed.vue'

const { t } = useI18n()
const { formatDuration } = useFormatDuration()
const notifications = useNotificationsStore()

const data = ref(null)
const loading = ref(false)
const error = ref('')

// Reuse the singleton connection initialised by MainLayout.
const { connected, refreshTick, onEvent } = useConnectionStatus()

const EVENT_CATEGORY = {
  device_online: 'device',
  device_offline: 'device',
  unknown_device_detected: 'device',
  camera_online: 'camera',
  camera_offline: 'camera',
  recording_started: 'camera',
  recording_completed: 'camera',
  recording_failed: 'camera',
  member_arrived: 'member',
  member_left: 'member',
  scan_completed: 'system',
  dlna_discover_completed: 'system',
  dlna_cast_started: 'system',
}

// Only these event types actually change the dashboard snapshot.
const DASHBOARD_REFRESH_EVENTS = new Set([
  'device_online',
  'device_offline',
  'unknown_device_detected',
  'scan_completed',
  'camera_online',
  'camera_offline',
  'recording_started',
  'recording_completed',
  'recording_failed',
  'member_arrived',
  'member_left',
])

function eventLabel(msg) {
  const d = msg.data || {}
  switch (msg.event) {
    case 'device_online':
      return t('dashboard.event_device_online', d)
    case 'device_offline':
      return t('dashboard.event_device_offline', d)
    case 'unknown_device_detected':
      return t('dashboard.event_unknown_device', d)
    case 'camera_online':
      return t('dashboard.event_camera_online', d)
    case 'camera_offline':
      return t('dashboard.event_camera_offline', d)
    case 'recording_started':
      return t('dashboard.event_recording_started', d)
    case 'recording_completed':
      return t('dashboard.event_recording_completed', d)
    case 'recording_failed':
      return t('dashboard.event_recording_failed', d)
    case 'member_arrived':
      return t('dashboard.event_member_arrived', d)
    case 'member_left':
      return t('dashboard.event_member_left', d)
    case 'scan_completed':
      return t('dashboard.event_scan_completed')
    case 'dlna_discover_completed':
      return t('dashboard.event_dlna_discover')
    case 'dlna_cast_started':
      return t('dashboard.event_dlna_cast')
    default:
      return msg.event
  }
}

const recentEvents = computed(() =>
  notifications.messages.slice(0, 20).map((msg) => ({
    category: EVENT_CATEGORY[msg.event] || 'system',
    label: eventLabel(msg),
  })),
)

let timer = null
let _unsubEvents = null

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

function startPolling() {
  if (timer) return
  timer = setInterval(fetchDashboard, 30000)
}

function stopPolling() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

function isDashboardEvent(msg) {
  if (!msg || typeof msg.event !== 'string') return false
  return DASHBOARD_REFRESH_EVENTS.has(msg.event)
}

onMounted(() => {
  fetchDashboard()
  if (!connected.value) startPolling()
  // Refetch whenever a relevant WS event arrives. The notifications store
  // already handles the side-effect of updating other stores; we just need
  // to refresh our snapshot. We do NOT listen to every event — only the ones
  // that change the dashboard numbers.
  _unsubEvents = onEvent((msg) => {
    if (isDashboardEvent(msg)) fetchDashboard()
  })
})

onUnmounted(() => {
  stopPolling()
  if (_unsubEvents) _unsubEvents()
})

// When WS is healthy, real-time events drive refetch; no need for 30s polling.
// When WS is down, fall back to polling so the user still sees fresh data.
watch(connected, (isConnected) => {
  if (isConnected) {
    stopPolling()
  } else {
    startPolling()
  }
})

// User-triggered force refresh (e.g. clicking the banner refresh button).
watch(refreshTick, () => {
  fetchDashboard()
})
</script>

<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">{{ $t('dashboard.title') }}</h2>
      <el-button :icon="Refresh" :loading="loading" @click="fetchDashboard">{{
        $t('common.refresh')
      }}</el-button>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon style="margin-bottom: 16px" />
    <el-skeleton v-if="!data && loading" :rows="4" animated />

    <template v-if="data">
      <div class="stats-grid">
        <StatCard
          :title="$t('dashboard.membersHome')"
          :value="data.members_home"
          :total="data.members_total"
          :description="$t('dashboard.membersHomeDesc')"
          variant="members"
          :style="{ animationDelay: '0ms' }"
        >
          <template #icon>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              aria-hidden="true"
            >
              <circle cx="9" cy="7" r="4" />
              <path d="M3 21v-2a7 7 0 0 1 10-5.5" />
              <circle cx="17" cy="8" r="3" />
              <path d="M14 21v-2a5 5 0 0 1 3.5-4.8" />
            </svg>
          </template>
        </StatCard>

        <StatCard
          :title="$t('dashboard.cameras')"
          :value="data.cameras_online"
          :total="data.cameras_total"
          :description="$t('dashboard.camerasOnline')"
          variant="cameras"
          :style="{ animationDelay: '40ms' }"
        >
          <template #icon>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              aria-hidden="true"
            >
              <path
                d="M2 8.5A2.5 2.5 0 0 1 4.5 6h9A2.5 2.5 0 0 1 16 8.5v7a2.5 2.5 0 0 1-2.5 2.5h-9A2.5 2.5 0 0 1 2 15.5v-7Z"
              />
              <path d="m17 10 4.5-3v10L17 14" />
            </svg>
          </template>
          <template #suffix>
            <span v-if="data.cameras_recording > 0" class="tag-recording">
              · {{ data.cameras_recording }}{{ $t('dashboard.camerasRecording') }}
            </span>
          </template>
        </StatCard>

        <StatCard
          :title="$t('dashboard.networkDevices')"
          :value="data.devices_online"
          :total="data.devices_total"
          :description="$t('dashboard.devicesOnline')"
          variant="devices"
          :style="{ animationDelay: '80ms' }"
        >
          <template #icon>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              aria-hidden="true"
            >
              <rect x="2" y="3" width="20" height="12" rx="2" />
              <path d="M8 21h8" />
              <path d="M12 15v6" />
            </svg>
          </template>
        </StatCard>

        <StatCard
          :title="$t('dashboard.todayRecordings')"
          :value="data.recordings_today_count"
          :description="
            $t('common.unit_record') +
            ' · ' +
            formatDuration(data.recordings_today_duration_seconds)
          "
          variant="recordings"
          :style="{ animationDelay: '120ms' }"
        >
          <template #icon>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="10" />
              <polygon
                points="10 8 16 12 10 16 10 8"
                fill="currentColor"
                stroke="none"
                opacity=".85"
              />
            </svg>
          </template>
        </StatCard>

        <StatCard
          :title="$t('dashboard.unknownDevices')"
          :value="data.unknown_devices_today"
          :description="$t('dashboard.todayAppeared')"
          variant="unknown"
          :warning="data.unknown_devices_today > 0"
          :style="{ animationDelay: '160ms' }"
        >
          <template #icon>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="10" />
              <path d="M12 16v-4" />
              <circle cx="12" cy="8" r=".5" fill="currentColor" />
            </svg>
          </template>
        </StatCard>
      </div>

      <ActivityFeed :items="recentEvents" :max-height="420" :show-view-all="true" />
    </template>
  </div>
</template>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.tag-recording {
  color: var(--color-error);
  font-weight: 600;
}
</style>
