<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useDevicesStore } from '@/stores/devices'
import { updateDevice, deleteDevice } from '@/api/devices'
import { ElMessage, ElMessageBox } from 'element-plus'
import FilterChip from '@/components/FilterChip.vue'
import EmptyState from '@/components/EmptyState.vue'
import { Refresh, Search } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import ScanProgress from '@/components/ScanProgress.vue'
import DeviceCard from '@/components/DeviceCard.vue'

const { t } = useI18n()
const route = useRoute()
const devicesStore = useDevicesStore()
const searchInput = ref('')

function onAllClick() {
  searchInput.value = ''
  devicesStore.filterTypes = []
  devicesStore.clearSearch()
}

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

function formatTime(val) {
  if (!val) return '—'
  return new Date(val).toLocaleString('zh-CN', { hour12: false })
}

const detailTypeLabel = computed(() => {
  const type = detailDevice.value?.device_type
  return type ? t(`common.deviceTypes.${type}`) : '—'
})


// ── 其他 ─────────────────────────────────────────────
const deviceTypeOptions = [
  'camera', 'computer', 'phone', 'iot',
  'router', 'tablet', 'tv', 'printer', 'smart_speaker', 'game_console', 'nas', 'wearable',
  'unknown',
]

// Filter chips reference --color-type-* tokens directly. FilterChip supports
// `var(...)` strings and uses color-mix() to derive alpha tints.
const filterOptions = deviceTypeOptions.map((value) => ({
  value,
  label: value,
  color: `var(--color-type-${value})`,
}))

onMounted(() => {
  if (route.query.mac) {
    searchInput.value = route.query.mac
    devicesStore.setSearch(route.query.mac)
  }
  devicesStore.fetchDevices()
})
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
        @input="devicesStore.setSearch(searchInput)"
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

    <div v-if="devicesStore.loading" class="device-grid">
      <div v-for="i in 6" :key="i" class="device-skeleton glass-card" />
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

    <div v-else class="device-grid">
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

    
    <!-- 详情弹窗 -->
    <el-dialog v-model="detailDialog" :title="$t('devices.detailTitle')" width="500px" v-if="detailDevice">
      <div class="detail-header">
        <span class="detail-status-dot" :class="detailDevice.is_online ? 'online' : 'offline'" />
        <span class="detail-title">{{ detailDevice.alias || detailDevice.hostname || $t('devices.unnamedDevice') }}</span>
        <el-tag :type="detailDevice.is_online ? 'success' : 'info'" size="small" style="margin-left: 8px">
          {{ detailDevice.is_online ? $t('common.online') : $t('common.offline') }}
        </el-tag>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">{{ $t('devices.basicInfo') }}</div>
        <div class="detail-grid">
          <div class="detail-row"><span class="detail-label">{{ $t('devices.deviceType') }}</span><span class="detail-value">{{ detailTypeLabel }}</span></div>
          <div class="detail-row"><span class="detail-label">{{ $t('devices.mac') }}</span><span class="detail-value mono">{{ detailDevice.mac }}</span></div>
          <div class="detail-row"><span class="detail-label">IP</span><span class="detail-value mono">{{ detailDevice.ip || '—' }}</span></div>
          <div class="detail-row"><span class="detail-label">{{ $t('devices.vendor') }}</span><span class="detail-value">{{ detailDevice.vendor || '—' }}</span></div>
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
/* Filter bar */
.filter-bar {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.search-input {
  width: 280px;
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

/* Device grid */
.device-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-4);
}

.device-skeleton {
  height: 200px;
  animation: shimmer 1.4s ease infinite;
  background: linear-gradient(
    90deg,
    var(--color-surface-raised) 25%,
    var(--color-surface-overlay) 37%,
    var(--color-surface-raised) 63%
  );
  background-size: 400% 100%;
}

@keyframes shimmer {
  0%   { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
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
.detail-status-dot.online  { background: var(--color-online); box-shadow: 0 0 6px rgba(16,185,129,.5); }
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
