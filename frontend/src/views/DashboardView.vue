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
    timestamp: msg.timestamp,
  })),
)

const pageSummary = computed(() => {
  if (!data.value) return ''
  return t('dashboard.pageSummary', {
    online: data.value.devices_online,
    total: data.value.devices_total,
    recording: data.value.cameras_recording,
  })
})

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
  _unsubEvents = onEvent((msg) => {
    if (isDashboardEvent(msg)) fetchDashboard()
  })
})

onUnmounted(() => {
  stopPolling()
  if (_unsubEvents) _unsubEvents()
})

watch(connected, (isConnected) => {
  if (isConnected) {
    stopPolling()
  } else {
    startPolling()
  }
})

watch(refreshTick, () => {
  fetchDashboard()
})
</script>

<template>
  <div class="dashboard-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ $t('dashboard.title') }}</h2>
        <span v-if="data" class="page-sub">{{ pageSummary }}</span>
        <span v-else class="page-sub">{{ $t('dashboard.subtitle') }}</span>
      </div>
      <div class="header-actions">
        <span
          class="live-badge"
          :class="connected ? 'live-badge--live' : 'live-badge--poll'"
          role="status"
        >
          <span class="live-dot" />
          {{ connected ? $t('dashboard.liveRealtime') : $t('dashboard.livePolling') }}
        </span>
        <el-button :icon="Refresh" :loading="loading" @click="fetchDashboard">
          {{ $t('common.refresh') }}
        </el-button>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon class="dashboard-alert" />

    <div v-if="!data && loading" class="stats-grid">
      <div v-for="i in 5" :key="i" class="stats-skeleton glass-card">
        <el-skeleton :rows="2" animated />
      </div>
    </div>

    <template v-if="data">
      <div class="stats-grid">
        <router-link to="/members" class="stat-card-link">
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
        </router-link>

        <router-link to="/cameras" class="stat-card-link">
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
        </router-link>

        <router-link to="/devices" class="stat-card-link">
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
        </router-link>

        <router-link to="/recordings" class="stat-card-link">
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
        </router-link>

        <router-link to="/devices" class="stat-card-link">
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
        </router-link>
      </div>

      <ActivityFeed :items="recentEvents" :max-height="420" />
    </template>
  </div>
</template>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.dashboard-alert {
  margin-bottom: 0;
}

.live-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  border: 1px solid var(--color-border-subtle);
  background: var(--color-surface-raised);
  color: var(--color-text-secondary);
}

.live-badge--live {
  border-color: color-mix(in srgb, var(--color-online) 35%, transparent);
  background: color-mix(in srgb, var(--color-online) 10%, transparent);
  color: var(--color-online);
}

.live-badge--poll {
  border-color: color-mix(in srgb, var(--color-warning) 35%, transparent);
  background: color-mix(in srgb, var(--color-warning) 10%, transparent);
  color: var(--color-warning);
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.live-badge--live .live-dot {
  animation: pulse-live 2s ease-in-out infinite;
}

@keyframes pulse-live {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(0.85);
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--space-4);
}

.stats-skeleton {
  padding: var(--space-5);
  min-height: 108px;
}

.stat-card-link {
  display: block;
  text-decoration: none;
  color: inherit;
  border-radius: var(--radius-xl);
  transition: transform var(--duration-base) var(--easing-snap);
}

.stat-card-link:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.stat-card-link:hover :deep(.stat-card) {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
}

.tag-recording {
  color: var(--color-error);
  font-weight: 600;
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .header-actions {
    flex-wrap: wrap;
    justify-content: flex-end;
  }
}
</style>
