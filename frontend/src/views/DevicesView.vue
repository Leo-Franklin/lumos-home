<script setup>
import { ref, computed, onMounted } from 'vue'
import { useDevicesStore } from '@/stores/devices'
import { updateDevice, deleteDevice, getDeviceHeatmap } from '@/api/devices'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import ScanProgress from '@/components/ScanProgress.vue'
import DeviceCard from '@/components/DeviceCard.vue'
import HeatmapChart from '@/components/charts/HeatmapChart.vue'

const { t } = useI18n()
const devicesStore = useDevicesStore()

// ── 编辑 ──────────────────────────────────────────────
const editDialog = ref(false)
const editForm = ref({})

function openEdit(row) {
  editForm.value = { ...row }
  editDialog.value = true
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
  } catch {
    ElMessage.error(t('devices.saveFailed'))
  }
}

// ── 删除 ──────────────────────────────────────────────
async function handleDelete(row) {
  await ElMessageBox.confirm(t('devices.deleteConfirm', { name: row.alias || row.mac }), t('common.confirmDelete'), { type: 'warning' })
  await deleteDevice(row.mac)
  ElMessage.success(t('devices.deleted'))
  devicesStore.fetchDevices()
}

// ── 详情 ──────────────────────────────────────────────
const detailDialog = ref(false)
const detailDevice = ref(null)

function openDetail(row) {
  detailDevice.value = row
  detailDialog.value = true
}

function parsePorts(raw) {
  if (!raw) return '—'
  try {
    const ports = JSON.parse(raw)
    return ports.length ? ports.join(', ') : '—'
  } catch {
    return raw
  }
}

function formatTime(val) {
  if (!val) return '—'
  return new Date(val).toLocaleString('zh-CN', { hour12: false })
}

const detailTypeLabel = computed(() => {
  const type = detailDevice.value?.device_type
  return type ? t(`common.deviceTypes.${type}`) : '—'
})

// ── Heatmap ──────────────────────────────────────────
const heatmapDialog  = ref(false)
const heatmapRange   = ref('7d')
const heatmapTypes   = ref([])
const heatmapData    = ref([])
const heatmapLoading = ref(false)

async function openHeatmap() {
  heatmapData.value  = []
  heatmapDialog.value = true
  await fetchHeatmap()
}

async function fetchHeatmap() {
  heatmapLoading.value = true
  try {
    const params = { range: heatmapRange.value }
    if (heatmapTypes.value.length) params.device_type = heatmapTypes.value.join(',')
    const { data } = await getDeviceHeatmap(params)
    heatmapData.value = data.cells ?? []
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('devices.heatmapFailed'))
  } finally {
    heatmapLoading.value = false
  }
}

// ── 其他 ─────────────────────────────────────────────
const deviceTypeOptions = [
  'camera', 'computer', 'phone', 'iot',
  'router', 'tablet', 'tv', 'printer', 'smart_speaker', 'game_console', 'nas', 'wearable',
  'unknown',
]

const filterOptions = [
  { value: 'camera',        label: 'Camera',        hex: '#5E5CE6' },
  { value: 'computer',      label: 'Computer',      hex: '#26C281' },
  { value: 'phone',         label: 'Phone',         hex: '#F2C94C' },
  { value: 'iot',           label: 'IoT',           hex: '#F07D38' },
  { value: 'router',        label: 'Router',        hex: '#06B6D4' },
  { value: 'tablet',        label: 'Tablet',        hex: '#D946EF' },
  { value: 'tv',            label: 'TV',            hex: '#7C3AED' },
  { value: 'printer',       label: 'Printer',       hex: '#14B8A6' },
  { value: 'smart_speaker', label: 'Smart Speaker', hex: '#A3E635' },
  { value: 'game_console',  label: 'Game Console',  hex: '#EF4444' },
  { value: 'nas',           label: 'NAS',           hex: '#60A5FA' },
  { value: 'wearable',      label: 'Wearable',      hex: '#FB7185' },
  { value: 'unknown',       label: 'Unknown',       hex: '#8B8B96' },
]

onMounted(() => devicesStore.fetchDevices())
</script>

<template>
  <div>
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ $t('devices.title') }}</h2>
        <span class="page-sub">
          {{ $t('devices.onlineCount', { online: devicesStore.items.filter((d) => d.is_online).length, total: devicesStore.total }) }}
        </span>
      </div>
      <div class="header-actions">
        <ScanProgress />
        <el-button @click="openHeatmap">{{ $t('devices.heatmap') }}</el-button>
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
      <button
        class="filter-btn"
        :class="{ active: devicesStore.filterTypes.length === 0 }"
        @click="devicesStore.toggleFilter('')"
      >
        {{ $t('common.all') }}
      </button>
      <button
        v-for="opt in filterOptions"
        :key="opt.value"
        class="filter-btn"
        :class="{ active: devicesStore.filterTypes.includes(opt.value) }"
        :style="devicesStore.filterTypes.includes(opt.value) ? { color: opt.hex, borderColor: opt.hex + '66', background: opt.hex + '18' } : {}"
        @click="devicesStore.toggleFilter(opt.value)"
      >
        {{ opt.label }}
      </button>
      <button
        v-if="devicesStore.filterTypes.length > 0"
        class="filter-btn filter-btn--clear"
        @click="devicesStore.toggleFilter('')"
      >
        {{ $t('devices.clearFilter') }}
      </button>
    </div>

    <div class="device-list" v-loading="devicesStore.loading">
      <DeviceCard
        v-for="device in devicesStore.items"
        :key="device.mac"
        :device="device"
        @detail="openDetail"
        @edit="openEdit"
        @delete="handleDelete"
      />
      <div v-if="!devicesStore.loading && devicesStore.items.length === 0" class="empty-state">
        {{ devicesStore.filterTypes.length > 0 ? $t('devices.noFilteredDevices') : $t('devices.noDevices') }}
      </div>
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
            <el-option v-for="t in deviceTypeOptions" :key="t" :label="$t(`common.deviceTypes.${t}`)" :value="t" />
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

    <!-- 热力图 -->
    <el-dialog v-model="heatmapDialog" :title="$t('devices.heatmapTitle')" width="760px" destroy-on-close>
      <el-skeleton v-if="heatmapLoading" :rows="4" animated />
      <HeatmapChart
        v-else
        :data="heatmapData"
        :range="heatmapRange"
        :device-types="heatmapTypes"
        :height="220"
        @range-change="(r) => { heatmapRange = r; fetchHeatmap() }"
        @type-filter-change="(t) => { heatmapTypes = t; fetchHeatmap() }"
      />
    </el-dialog>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailDialog" :title="$t('devices.detailTitle')" width="500px" v-if="detailDevice">
      <div class="detail-header">
        <span class="detail-status-dot" :class="detailDevice.is_online ? 'online' : 'offline'" />
        <span class="detail-title">{{ detailDevice.alias || detailDevice.mac }}</span>
        <el-tag :type="detailDevice.is_online ? 'success' : 'info'" size="small" style="margin-left: 8px">
          {{ detailDevice.is_online ? $t('common.online') : $t('common.offline') }}
        </el-tag>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">{{ $t('devices.basicInfo') }}</div>
        <div class="detail-grid">
          <div class="detail-row"><span class="detail-label">{{ $t('devices.macAddress') }}</span><span class="detail-value mono">{{ detailDevice.mac }}</span></div>
          <div class="detail-row"><span class="detail-label">{{ $t('devices.ipAddress') }}</span><span class="detail-value mono">{{ detailDevice.ip || '—' }}</span></div>
          <div class="detail-row"><span class="detail-label">{{ $t('devices.hostname') }}</span><span class="detail-value mono">{{ detailDevice.hostname || '—' }}</span></div>
          <div class="detail-row"><span class="detail-label">{{ $t('devices.deviceType') }}</span><span class="detail-value">{{ detailTypeLabel }}</span></div>
          <div class="detail-row"><span class="detail-label">{{ $t('devices.vendor') }}</span><span class="detail-value">{{ detailDevice.vendor || '—' }}</span></div>
        </div>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">{{ $t('devices.networkInfo') }}</div>
        <div class="detail-grid">
          <div class="detail-row"><span class="detail-label">{{ $t('devices.openPorts') }}</span><span class="detail-value mono">{{ parsePorts(detailDevice.open_ports) }}</span></div>
          <div class="detail-row"><span class="detail-label">{{ $t('devices.responseTime') }}</span><span class="detail-value mono">{{ detailDevice.response_time_ms != null ? detailDevice.response_time_ms + ' ms' : '—' }}</span></div>
        </div>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">{{ $t('devices.recordInfo') }}</div>
        <div class="detail-grid">
          <div class="detail-row"><span class="detail-label">{{ $t('devices.firstSeen') }}</span><span class="detail-value">{{ formatTime(detailDevice.created_at) }}</span></div>
          <div class="detail-row"><span class="detail-label">{{ $t('devices.lastSeen') }}</span><span class="detail-value">{{ formatTime(detailDevice.last_seen) }}</span></div>
        </div>
      </div>

      <div class="detail-section" v-if="detailDevice.notes">
        <div class="detail-section-title">{{ $t('devices.notes') }}</div>
        <div class="detail-notes">{{ detailDevice.notes }}</div>
      </div>

      <template #footer>
        <el-button @click="detailDialog = false">{{ $t('common.close') }}</el-button>
        <el-button type="primary" @click="detailDialog = false; openEdit(detailDevice)">{{ $t('common.edit') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* 过滤栏 */
.filter-bar {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.filter-btn {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-family: var(--font-sans);
  padding: 4px 12px;
  border-radius: var(--radius-full);
  cursor: pointer;
  line-height: 1.5;
  transition: background var(--duration-fast) ease-out,
              color var(--duration-fast) ease-out,
              border-color var(--duration-fast) ease-out;
}
.filter-btn:hover:not(.active) {
  background: var(--color-surface-overlay);
  color: var(--color-text-primary);
}
.filter-btn.active {
  font-weight: 500;
}
.filter-btn--clear {
  color: var(--color-text-muted);
  border-color: transparent;
}
.filter-btn--clear:hover {
  color: var(--color-error, #f05252);
  border-color: rgba(240, 82, 82, 0.3);
  background: rgba(240, 82, 82, 0.08);
}

.device-list {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-surface);
}

.empty-state {
  padding: 40px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--color-text-muted);
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
.detail-status-dot.online  { background: var(--color-online); box-shadow: 0 0 6px rgba(38,194,129,.5); }
.detail-status-dot.offline { background: var(--color-offline); }
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
</style>
