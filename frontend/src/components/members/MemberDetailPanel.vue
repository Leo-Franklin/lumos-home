<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatDuration } from '@/composables/useFormatDuration'
import { useApiError } from '@/composables/useApiError'
import {
  listMemberDevices,
  bindDevice,
  unbindDevice,
  listPresenceLogs,
  getMemberStats,
} from '@/api/members'
import { ElMessage } from 'element-plus'
import { Delete, Edit } from '@element-plus/icons-vue'
import ActionButtonGroup from '@/components/common/ActionButtonGroup.vue'
import EmptyState from '@/components/EmptyState.vue'
import { resolveDeviceLabel, buildDeviceMap } from '@/utils/memberDeviceLabel'

const props = defineProps({
  member: { type: Object, required: true },
  allDevices: { type: Array, default: () => [] },
  allCameras: { type: Array, default: () => [] },
  deviceMap: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['edit', 'delete', 'devices-changed'])

const { t } = useI18n()
const { formatDuration } = useFormatDuration()
const handleError = useApiError()

const automationOpen = ref(false)

// ── Bound devices ──────────────────────────────────────────
const boundDevices = ref([])
const devicesLoading = ref(false)
const bindForm = ref({ mac: '', label: '' })

async function loadBoundDevices() {
  devicesLoading.value = true
  try {
    const { data } = await listMemberDevices(props.member.id)
    boundDevices.value = data
  } finally {
    devicesLoading.value = false
  }
}

const unboundDevices = computed(() =>
  props.allDevices.filter((d) => !boundDevices.value.some((b) => b.mac === d.mac)),
)

async function handleBind() {
  if (!bindForm.value.mac) return
  try {
    await bindDevice(props.member.id, {
      mac: bindForm.value.mac,
      label: bindForm.value.label || null,
    })
    ElMessage.success(t('members.bound'))
    bindForm.value = { mac: '', label: '' }
    await loadBoundDevices()
    emit('devices-changed')
  } catch (e) {
    handleError(e, 'members.bindFailed')
  }
}

async function handleUnbind(mac) {
  await unbindDevice(props.member.id, mac)
  ElMessage.success(t('members.unbound'))
  await loadBoundDevices()
  emit('devices-changed')
}

function deviceLabel(row) {
  return resolveDeviceLabel(row.mac, {
    ...props.deviceMap,
    ...buildDeviceMap(boundDevices.value),
  })
}

function cameraLabel(cam) {
  return cam.alias || cam.onvif_host || cam.device_mac
}

// ── Presence logs ──────────────────────────────────────────
const logs = ref([])
const logsTotal = ref(0)
const logsPage = ref(1)
const logsLoading = ref(false)

async function loadLogs() {
  logsLoading.value = true
  try {
    const { data } = await listPresenceLogs(props.member.id, {
      page: logsPage.value,
      page_size: 20,
    })
    logs.value = data.items
    logsTotal.value = data.total
  } finally {
    logsLoading.value = false
  }
}

function handleLogsPageChange(p) {
  logsPage.value = p
  loadLogs()
}

const groupedLogs = computed(() => {
  const groups = {}
  for (const log of logs.value) {
    const d = new Date(log.occurred_at)
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)
    const dateKey = new Date(d.getFullYear(), d.getMonth(), d.getDate())
    let label
    if (dateKey.getTime() === today.getTime()) label = t('charts.date.today')
    else if (dateKey.getTime() === yesterday.getTime()) label = t('charts.date.yesterday')
    else label = t('charts.date.fallback', { m: d.getMonth() + 1, d: d.getDate() })
    if (!groups[label]) groups[label] = []
    groups[label].push(log)
  }
  return groups
})

function formatLogTime(iso) {
  const d = new Date(iso)
  const h = d.getHours().toString().padStart(2, '0')
  const m = d.getMinutes().toString().padStart(2, '0')
  return `${h}:${m}`
}

function logDeviceLabel(mac) {
  return resolveDeviceLabel(mac, props.deviceMap)
}

// ── Stats ──────────────────────────────────────────────────
const statsRange = ref('7d')
const statsData = ref(null)
const statsLoading = ref(false)

async function fetchMemberStats() {
  statsLoading.value = true
  try {
    const { data } = await getMemberStats(props.member.id, { range: statsRange.value })
    statsData.value = data
  } catch (e) {
    handleError(e, 'members.statsFailed')
  } finally {
    statsLoading.value = false
  }
}

function statsDailyMax() {
  return Math.max(...(statsData.value?.daily || []).map((d) => d.minutes), 1)
}

const autoRecordLabels = computed(() => {
  const macs = props.member.auto_record_cameras || []
  if (!macs.length) return []
  return macs.map((mac) => {
    const cam = props.allCameras.find((c) => c.device_mac === mac)
    return cam ? cameraLabel(cam) : mac
  })
})

async function reloadAll() {
  logsPage.value = 1
  statsRange.value = '7d'
  await Promise.all([loadBoundDevices(), loadLogs(), fetchMemberStats()])
}

watch(
  () => props.member?.id,
  (id) => {
    if (id) reloadAll()
  },
  { immediate: true },
)
</script>

<template>
  <div class="detail-panel">
    <div class="panel-head">
      <div class="panel-identity">
        <el-avatar v-if="member.avatar_url" :src="member.avatar_url" :size="40" />
        <el-avatar v-else :size="40">{{ member.name.charAt(0) }}</el-avatar>
        <div>
          <div class="panel-name">{{ member.name }}</div>
          <div class="panel-status-row">
            <span
              class="status-dot"
              :class="member.is_home ? 'status-dot--home' : 'status-dot--away'"
            />
            <span>{{ member.is_home ? $t('members.home') : $t('members.away') }}</span>
            <span v-if="member.is_home && member.last_arrived_at" class="panel-meta">
              {{ $t('members.lastArrived') }} {{ $d(member.last_arrived_at, 'short') }}
            </span>
            <span v-else-if="!member.is_home && member.last_left_at" class="panel-meta">
              {{ $t('members.lastLeft') }} {{ $d(member.last_left_at, 'short') }}
            </span>
          </div>
        </div>
      </div>
      <ActionButtonGroup
        :actions="[
          {
            icon: Edit,
            tooltip: $t('common.edit'),
            ariaLabel: $t('common.edit'),
            onClick: () => emit('edit', member),
          },
          {
            icon: Delete,
            tooltip: $t('common.delete'),
            ariaLabel: $t('common.delete'),
            danger: true,
            onClick: () => emit('delete', member),
          },
        ]"
      />
    </div>

    <!-- Devices -->
    <section class="detail-section">
      <div class="section-title">{{ $t('members.sectionDevices') }}</div>
      <div class="bind-row">
        <el-select
          v-model="bindForm.mac"
          :placeholder="$t('members.selectDevice')"
          filterable
          style="flex: 1"
          size="small"
        >
          <el-option
            v-for="d in unboundDevices"
            :key="d.mac"
            :label="`${d.alias || d.hostname || d.mac} (${d.ip})`"
            :value="d.mac"
          />
        </el-select>
        <el-input
          v-model="bindForm.label"
          :placeholder="$t('members.noteOptional')"
          style="width: 110px"
          size="small"
        />
        <el-button type="primary" size="small" @click="handleBind">{{
          $t('members.bindDevice')
        }}</el-button>
      </div>

      <div v-loading="devicesLoading" class="device-list">
        <div v-for="row in boundDevices" :key="row.mac" class="device-row">
          <div class="device-row-info">
            <span class="device-row-name">{{ deviceLabel(row) }}</span>
            <span
              class="device-row-online"
              :class="row.device_info?.is_online ? 'online' : 'offline'"
            >
              {{
                row.device_info?.is_online
                  ? $t('members.deviceOnline')
                  : $t('members.deviceOffline')
              }}
            </span>
          </div>
          <el-button type="danger" link size="small" @click="handleUnbind(row.mac)">
            {{ $t('members.unbind') }}
          </el-button>
        </div>
        <div v-if="!devicesLoading && !boundDevices.length" class="section-empty">
          {{ $t('members.noBoundDevicesHint') }}
        </div>
      </div>
    </section>

    <!-- Activity -->
    <section class="detail-section">
      <div class="section-title">{{ $t('members.sectionActivity') }}</div>
      <div v-loading="logsLoading" class="logs-scroll">
        <template v-if="logs.length">
          <div v-for="(group, dateLabel) in groupedLogs" :key="dateLabel" class="log-group">
            <div class="log-date-header">{{ dateLabel }}</div>
            <div class="log-timeline">
              <div v-for="log in group" :key="log.id" class="log-item">
                <div
                  class="log-dot"
                  :class="log.event === 'arrived' ? 'log-dot--arrive' : 'log-dot--leave'"
                />
                <div class="log-content">
                  <span class="log-time">{{ formatLogTime(log.occurred_at) }}</span>
                  <span
                    class="log-badge"
                    :class="log.event === 'arrived' ? 'log-badge--arrive' : 'log-badge--leave'"
                  >
                    {{ log.event === 'arrived' ? $t('members.arrived') : $t('members.left') }}
                  </span>
                  <span class="log-device">{{ logDeviceLabel(log.triggered_by_mac) }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>
        <EmptyState
          v-else-if="!logsLoading"
          compact
          size="small"
          icon="member"
          :title="$t('members.noData')"
        />
      </div>
      <div v-if="logsTotal > 0" class="logs-footer">
        <span class="logs-count">{{ logsTotal }} {{ $t('members.logRecords') }}</span>
        <el-pagination
          small
          layout="prev, pager, next"
          :total="logsTotal"
          :page-size="20"
          :current-page="logsPage"
          @current-change="handleLogsPageChange"
        />
      </div>
    </section>

    <!-- Stats -->
    <section class="detail-section">
      <div class="section-title-row">
        <span class="section-title">{{ $t('members.sectionStats') }}</span>
        <el-radio-group v-model="statsRange" size="small" @change="fetchMemberStats">
          <el-radio-button value="7d">{{ $t('members.recent7Days') }}</el-radio-button>
          <el-radio-button value="30d">{{ $t('members.recent30Days') }}</el-radio-button>
        </el-radio-group>
      </div>
      <div v-if="statsData && !statsLoading" class="stats-total">
        {{ $t('members.statsTotal', { duration: formatDuration(statsData.total_minutes * 60) }) }}
      </div>
      <el-skeleton v-if="statsLoading" :rows="3" animated />
      <div v-if="statsData && !statsLoading" class="daily-chart">
        <div v-for="d in statsData.daily" :key="d.date" class="daily-bar-col">
          <div
            class="daily-bar"
            :style="{ height: Math.max(4, (d.minutes / statsDailyMax()) * 72) + 'px' }"
            :title="`${d.date}: ${formatDuration(d.minutes * 60)}`"
          />
          <div class="daily-label">{{ d.date.slice(5) }}</div>
        </div>
        <div v-if="!statsData.daily?.length" class="section-empty">{{ $t('members.noData') }}</div>
      </div>
    </section>

    <!-- Automation (collapsed) -->
    <section class="detail-section detail-section--automation">
      <button type="button" class="automation-toggle" @click="automationOpen = !automationOpen">
        <span class="section-title">{{ $t('members.sectionAutomation') }}</span>
        <span class="automation-chevron" :class="{ open: automationOpen }">›</span>
      </button>
      <div v-show="automationOpen" class="automation-body">
        <div class="automation-row">
          <span class="automation-label">{{ $t('members.autoRecord') }}</span>
          <span v-if="autoRecordLabels.length" class="automation-value">
            {{ autoRecordLabels.join('、') }}
          </span>
          <span v-else class="automation-value muted">{{ $t('members.automationNone') }}</span>
        </div>
        <div class="automation-row">
          <span class="automation-label">{{ $t('members.webhook') }}</span>
          <span class="automation-value muted">{{ member.webhook_url || '—' }}</span>
        </div>
        <p class="automation-hint">{{ $t('members.automationHint') }}</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.detail-panel {
  display: flex;
  flex-direction: column;
  gap: 0;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border-subtle);
  margin-bottom: 4px;
}

.panel-identity {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.panel-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.panel-status-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--color-text-secondary);
  flex-wrap: wrap;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot--home {
  background: var(--color-online);
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.45);
}

.status-dot--away {
  background: var(--color-offline);
}

.panel-meta {
  color: var(--color-text-muted);
}

.detail-section {
  padding: 14px 0;
  border-bottom: 1px solid var(--color-border-subtle);
}

.detail-section:last-child {
  border-bottom: none;
}

.section-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 10px;
}

.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.section-title-row .section-title {
  margin-bottom: 0;
}

.bind-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
}

.device-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 32px;
}

.device-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  background: var(--color-surface-raised);
  border-radius: var(--radius-sm);
}

.device-row-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.device-row-name {
  font-size: 13px;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.device-row-online {
  font-size: 11px;
}

.device-row-online.online {
  color: var(--color-online);
}

.device-row-online.offline {
  color: var(--color-text-muted);
}

.section-empty {
  font-size: 12px;
  color: var(--color-text-muted);
  padding: 8px 0;
}

.logs-scroll {
  max-height: 160px;
  overflow-y: auto;
  padding-right: 4px;
}

.log-group {
  margin-bottom: 14px;
}

.log-date-header {
  font-size: 10px;
  font-weight: 600;
  color: var(--color-text-muted);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 6px;
  padding-left: 20px;
}

.log-timeline {
  position: relative;
  padding-left: 16px;
}

.log-timeline::before {
  content: '';
  position: absolute;
  left: 5px;
  top: 6px;
  bottom: 6px;
  width: 1px;
  background: var(--color-border-subtle);
}

.log-item {
  position: relative;
  display: flex;
  align-items: center;
  padding: 5px 0;
}

.log-dot {
  position: absolute;
  left: -14px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 2px solid;
  background: var(--color-surface);
  z-index: 1;
}

.log-dot--arrive {
  border-color: var(--color-online);
}

.log-dot--leave {
  border-color: var(--color-warning);
}

.log-content {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.log-time {
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-primary);
}

.log-badge {
  font-size: 10px;
  font-weight: 500;
  padding: 2px 6px;
  border-radius: 4px;
}

.log-badge--arrive {
  background: var(--color-primary-subtle);
  color: var(--color-online);
}

.log-badge--leave {
  background: var(--color-primary-subtle);
  color: var(--color-warning);
}

.log-device {
  font-size: 11px;
  color: var(--color-text-muted);
}

.logs-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.logs-count {
  font-size: 11px;
  color: var(--color-text-muted);
}

.stats-total {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.daily-chart {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  height: 72px;
  padding-bottom: 16px;
  overflow-x: auto;
}

.daily-bar-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 22px;
  flex: 1;
}

.daily-bar {
  width: 100%;
  background: var(--color-primary);
  border-radius: 2px 2px 0 0;
}

.daily-label {
  font-size: 9px;
  color: var(--color-text-muted);
  margin-top: 3px;
}

.automation-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0;
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
}

.automation-toggle .section-title {
  margin-bottom: 0;
}

.automation-chevron {
  color: var(--color-text-muted);
  font-size: 16px;
  transition: transform 0.15s ease;
}

.automation-chevron.open {
  transform: rotate(90deg);
}

.automation-body {
  margin-top: 10px;
}

.automation-row {
  display: flex;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
}

.automation-label {
  min-width: 72px;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.automation-value {
  color: var(--color-text-primary);
  word-break: break-all;
}

.automation-value.muted {
  color: var(--color-text-muted);
}

.automation-hint {
  font-size: 11px;
  color: var(--color-text-muted);
  margin: 8px 0 0;
  line-height: 1.5;
}
</style>
