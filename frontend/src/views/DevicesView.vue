<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDevicesStore } from '@/stores/devices'
import { updateDevice, deleteDevice } from '@/api/devices'
import { ElMessage } from 'element-plus'
import FilterChip from '@/components/FilterChip.vue'
import EmptyState from '@/components/EmptyState.vue'
import { Refresh, Search } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import ScanProgress from '@/components/ScanProgress.vue'
import DeviceCard from '@/components/DeviceCard.vue'
import { useApiError } from '@/composables/useApiError'
import { scheduleUndo } from '@/composables/useUndo'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const devicesStore = useDevicesStore()
const searchInput = ref('')
const handleError = useApiError()

/** URL ?mac= is the source of truth for deep-linked device filters. */
function applyRouteMacFilter(mac) {
  const q = mac ? String(mac) : ''
  searchInput.value = q
  if (q) {
    if (devicesStore.search === q) return
    devicesStore.search = q
    devicesStore.page = 1
    devicesStore.fetchDevices()
    return
  }
  if (devicesStore.search) {
    devicesStore.clearSearch()
    return
  }
  if (!devicesStore.items.length) {
    devicesStore.fetchDevices()
  }
}

watch(() => route.query.mac, applyRouteMacFilter, { immediate: true })

function onSearchInput(val) {
  devicesStore.setSearch(val)
  if (!val.trim() && route.query.mac) {
    router.replace({ path: '/devices' })
  }
}

function onAllClick() {
  searchInput.value = ''
  devicesStore.filterTypes = []
  if (route.query.mac) {
    router.replace({ path: '/devices' })
    return
  }
  devicesStore.clearSearch()
}

// ── 编辑 ──────────────────────────────────────────────
const editDialog = ref(false)
const editForm = ref({})

function openEdit(row) {
  editForm.value = { ...row }
  editDialog.value = true
}

function closeDetailAndEdit() {
  detailDialog.value = false
  if (detailDevice.value) {
    openEdit(detailDevice.value)
  }
}

async function saveEdit() {
  try {
    await updateDevice(editForm.value.mac, {
      alias: editForm.value.alias,
      device_type: editForm.value.device_type,
      notes: editForm.value.notes,
    })
    ElMessage.success(t('devices.saveSuccess'))
    editDialog.value = false
    devicesStore.fetchDevices()
  } catch (e) {
    handleError(e, 'devices.saveFailed')
  }
}

// ── 删除 ──────────────────────────────────────────────
async function handleDelete(row) {
  // P2-10: 撤销模式（5s 内可恢复）
  const originalIndex = devicesStore.items.findIndex((d) => d.mac === row.mac)
  if (originalIndex === -1) return
  // 1. 立即从 store 中隐藏
  devicesStore.items.splice(originalIndex, 1)
  if (devicesStore.total > 0) devicesStore.total -= 1
  // 2. 弹出 5s 撤销 toast
  scheduleUndo({
    label: t('devices.deleted'),
    performDelete: () => deleteDevice(row.mac),
    onUndo: () => {
      devicesStore.items.splice(originalIndex, 0, row)
      devicesStore.total += 1
    },
    onError: (e) => handleError(e, 'devices.saveFailed'),
  })
}

// ── 详情 ──────────────────────────────────────────────
const detailDialog = ref(false)
const detailDevice = ref(null)

function openDetail(row) {
  detailDevice.value = row
  detailDialog.value = true
}

function formatTime(val) {
  if (!val) return '—'
  return new Date(val).toLocaleString('zh-CN', { hour12: false })
}

const detailTypeLabel = computed(() => {
  const type = detailDevice.value?.device_type
  return type ? t(`common.deviceTypes.${type}`) : '—'
})

function parseJsonField(raw, fallback = null) {
  if (!raw) return fallback
  try {
    return JSON.parse(raw)
  } catch {
    return fallback
  }
}

const detailOpenPorts = computed(() => {
  const ports = parseJsonField(detailDevice.value?.open_ports, [])
  return Array.isArray(ports) ? ports : []
})

const detailScanMeta = computed(() => {
  const meta = parseJsonField(detailDevice.value?.scan_metadata, null)
  return meta && typeof meta === 'object' ? meta : null
})

const detailServicesLabel = computed(() => {
  const services = detailScanMeta.value?.services
  if (!Array.isArray(services) || services.length === 0) return '—'
  return services.map((s) => `${s.port}/${s.name}`).join(', ')
})

const detailTypeConfidence = computed(() => {
  const confidence = detailScanMeta.value?.type_confidence
  if (confidence === undefined || confidence === null) return '—'
  return `${Math.round(confidence * 100)}%`
})

const detailTypeSignals = computed(() => {
  const signals = detailScanMeta.value?.type_signals
  return Array.isArray(signals) ? signals : []
})

// ── 其他 ─────────────────────────────────────────────
const deviceTypeOptions = [
  'camera',
  'computer',
  'phone',
  'iot',
  'router',
  'tablet',
  'tv',
  'printer',
  'smart_speaker',
  'game_console',
  'nas',
  'wearable',
  'unknown',
]

// Filter chips reference --color-type-* tokens directly. FilterChip supports
// `var(...)` strings and uses color-mix() to derive alpha tints.
const filterOptions = deviceTypeOptions.map((value) => ({
  value,
  label: value,
  color: `var(--color-type-${value})`,
}))
</script>

<template>
  <div>
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ $t('devices.title') }}</h2>
        <span class="page-sub">
          {{
            $t('devices.onlineCount', {
              online: devicesStore.items.filter((d) => d.is_online).length,
              total: devicesStore.total,
            })
          }}
        </span>
      </div>
      <div class="header-actions">
        <ScanProgress />
        <el-button
          type="primary"
          :loading="devicesStore.scanning"
          :icon="Refresh"
          @click="devicesStore.scan()"
        >
          {{ $t('devices.scan') }}
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-input
        v-model="searchInput"
        :placeholder="$t('devices.searchPlaceholder')"
        clearable
        class="search-input"
        @input="onSearchInput"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <div class="filter-chips">
        <FilterChip
          :label="$t('common.all')"
          :active="devicesStore.filterTypes.length === 0"
          @click="onAllClick"
        />
        <FilterChip
          v-for="opt in filterOptions"
          :key="opt.value"
          :label="$t(`common.deviceTypes.${opt.value}`)"
          :active="devicesStore.filterTypes.includes(opt.value)"
          :color="opt.color"
          @click="devicesStore.toggleFilter(opt.value)"
        />
      </div>
    </div>

    <div v-if="devicesStore.loading" class="device-list">
      <el-skeleton :rows="3" animated class="device-list-skeleton" />
    </div>

    <div v-else-if="devicesStore.items.length === 0" class="empty-container">
      <EmptyState
        :title="$t('devices.noDevices')"
        :description="$t('devices.noDevicesHint')"
        icon="device"
        :action-label="$t('devices.scan')"
        @action="devicesStore.scan()"
      />
    </div>

    <div v-else class="device-list">
      <DeviceCard
        v-for="device in devicesStore.items"
        :key="device.mac"
        :device="device"
        @detail="openDetail"
        @edit="openEdit"
        @delete="handleDelete"
      />
    </div>

    <!-- 分页 -->
    <div class="pagination-bar" v-if="devicesStore.total > 0">
      <el-pagination
        v-model:current-page="devicesStore.page"
        v-model:page-size="devicesStore.pageSize"
        :total="devicesStore.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="devicesStore.changePage"
        @size-change="devicesStore.changePageSize"
      />
    </div>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="editDialog" :title="$t('devices.editDevice')" width="440px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item :label="$t('devices.mac')">
          <el-input :value="editForm.mac" disabled />
        </el-form-item>
        <el-form-item :label="$t('devices.alias')">
          <el-input v-model="editForm.alias" :placeholder="$t('devices.alias')" />
        </el-form-item>
        <el-form-item :label="$t('devices.deviceType')">
          <el-select v-model="editForm.device_type" style="width: 100%">
            <el-option
              v-for="t in deviceTypeOptions"
              :key="t"
              :label="$t(`common.deviceTypes.${t}`)"
              :value="t"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('devices.notes')">
          <el-input v-model="editForm.notes" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="saveEdit">{{ $t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailDialog"
      :title="$t('devices.detailTitle')"
      width="500px"
      v-if="detailDevice"
    >
      <div class="detail-header">
        <span
          class="detail-status-dot"
          :class="detailDevice.is_online ? 'online' : 'offline'"
          role="status"
          :aria-label="detailDevice.is_online ? $t('common.online') : $t('common.offline')"
        />
        <span class="detail-title">{{
          detailDevice.alias || detailDevice.hostname || $t('devices.unnamedDevice')
        }}</span>
        <el-tag
          :type="detailDevice.is_online ? 'success' : 'info'"
          size="small"
          style="margin-left: 8px"
        >
          {{ detailDevice.is_online ? $t('common.online') : $t('common.offline') }}
        </el-tag>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">{{ $t('devices.basicInfo') }}</div>
        <div class="detail-grid">
          <div class="detail-row">
            <span class="detail-label">{{ $t('devices.deviceType') }}</span>
            <span class="detail-value">
              {{ detailTypeLabel }}
              <template v-if="detailTypeConfidence !== '—'">
                · {{ detailTypeConfidence }}
              </template>
            </span>
          </div>
          <div class="detail-row">
            <span class="detail-label">{{ $t('devices.mac') }}</span>
            <span class="detail-value mono">{{ detailDevice.mac }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">IP</span>
            <span class="detail-value mono">{{ detailDevice.ip || '—' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">{{ $t('devices.vendor') }}</span>
            <span class="detail-value">{{ detailDevice.vendor || '—' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">{{ $t('devices.hostname') }}</span>
            <span class="detail-value">{{ detailDevice.hostname || '—' }}</span>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">{{ $t('devices.networkInfo') }}</div>
        <div class="detail-grid">
          <div class="detail-row">
            <span class="detail-label">{{ $t('devices.responseTime') }}</span>
            <span class="detail-value">
              {{
                detailDevice.response_time_ms != null
                  ? `${detailDevice.response_time_ms} ${$t('devices.ms')}`
                  : '—'
              }}
            </span>
          </div>
          <div class="detail-row">
            <span class="detail-label">{{ $t('devices.openPorts') }}</span>
            <span class="detail-value mono">
              {{ detailOpenPorts.length ? detailOpenPorts.join(', ') : '—' }}
            </span>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">{{ $t('devices.scanInfo') }}</div>
        <div v-if="detailScanMeta" class="detail-grid">
          <div class="detail-row" v-if="detailScanMeta.netbios_name">
            <span class="detail-label">{{ $t('devices.netbiosName') }}</span>
            <span class="detail-value">{{ detailScanMeta.netbios_name }}</span>
          </div>
          <div class="detail-row" v-if="detailScanMeta.os_hint">
            <span class="detail-label">{{ $t('devices.osHint') }}</span>
            <span class="detail-value">{{ detailScanMeta.os_hint }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">{{ $t('devices.typeConfidence') }}</span>
            <span class="detail-value">{{ detailTypeConfidence }}</span>
          </div>
          <div class="detail-row" v-if="detailTypeSignals.length">
            <span class="detail-label">{{ $t('devices.typeSignals') }}</span>
            <span class="detail-value">
              <span v-for="(signal, idx) in detailTypeSignals" :key="idx" class="signal-chip">
                {{ signal.source }}: {{ signal.reason }}
              </span>
            </span>
          </div>
          <div class="detail-row" v-if="detailScanMeta.upnp?.friendly_name">
            <span class="detail-label">{{ $t('devices.upnpName') }}</span>
            <span class="detail-value">{{ detailScanMeta.upnp.friendly_name }}</span>
          </div>
          <div class="detail-row" v-if="detailScanMeta.upnp?.model_name">
            <span class="detail-label">{{ $t('devices.upnpModel') }}</span>
            <span class="detail-value">{{ detailScanMeta.upnp.model_name }}</span>
          </div>
          <div class="detail-row" v-if="detailServicesLabel !== '—'">
            <span class="detail-label">{{ $t('devices.services') }}</span>
            <span class="detail-value mono">{{ detailServicesLabel }}</span>
          </div>
        </div>
        <div v-else class="detail-notes">{{ $t('devices.noScanInfo') }}</div>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">{{ $t('devices.recordInfo') }}</div>
        <div class="detail-grid">
          <div class="detail-row">
            <span class="detail-label">{{ $t('devices.firstSeen') }}</span>
            <span class="detail-value">{{ formatTime(detailDevice.created_at) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">{{ $t('devices.lastSeen') }}</span>
            <span class="detail-value">{{ formatTime(detailDevice.last_seen) }}</span>
          </div>
        </div>
      </div>

      <div class="detail-section" v-if="detailDevice.notes">
        <div class="detail-section-title">{{ $t('devices.notes') }}</div>
        <div class="detail-notes">{{ detailDevice.notes }}</div>
      </div>

      <template #footer>
        <el-button @click="detailDialog = false">{{ $t('common.close') }}</el-button>
        <el-button type="primary" @click="closeDetailAndEdit">{{ $t('common.edit') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* Filter bar */
.filter-bar {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.search-input {
  width: 280px;
  max-width: 100%;
}

@media (max-width: 767.98px) {
  .search-input {
    width: 100%;
  }
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

@media (max-width: 767.98px) {
  .filter-chips {
    flex-wrap: nowrap;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    padding-bottom: var(--space-1);
    margin: 0 calc(-1 * var(--space-1));
    padding-left: var(--space-1);
    padding-right: var(--space-1);
  }

  .filter-chips::-webkit-scrollbar {
    display: none;
  }
}

/* Device list (row layout, per DESIGN.md §9) */
.device-list {
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.device-list > :first-child {
  border-top: 0;
}

.device-list-skeleton {
  padding: var(--space-3) var(--space-4);
}
.device-list-skeleton :deep(.el-skeleton__item) {
  height: 52px;
  margin-bottom: var(--space-3);
  border-radius: 0;
}
.device-list-skeleton :deep(.el-skeleton__item:last-child) {
  margin-bottom: 0;
}

.empty-container {
  display: flex;
  justify-content: center;
  padding: var(--space-10) 0;
}

/* 详情弹窗 */
.detail-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}
.detail-status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.detail-status-dot.online {
  background: var(--color-online);
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.5);
}
.detail-status-dot.offline {
  background: var(--color-offline);
}
.detail-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.detail-section {
  margin-bottom: 16px;
}
.detail-section-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--color-border-subtle);
}
.detail-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.detail-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.detail-label {
  min-width: 80px;
  font-size: 12px;
  color: var(--color-text-muted);
  flex-shrink: 0;
}
.detail-value {
  font-size: 13px;
  color: var(--color-text-primary);
  word-break: break-all;
}
.detail-value.mono {
  font-family: var(--font-mono);
  font-size: 12px;
}
.detail-notes {
  font-size: 13px;
  color: var(--color-text-secondary);
  white-space: pre-wrap;
  line-height: 1.6;
}

.signal-chip {
  display: block;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}
</style>
