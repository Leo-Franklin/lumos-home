<script setup>
import { ref, watch, onMounted } from 'vue'
import { listSchedules, createSchedule, updateSchedule, deleteSchedule } from '@/api/schedules'
import { listCameras } from '@/api/cameras'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Clock, Calendar } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import CronSelector from '@/components/CronSelector.vue'
import ActionButtonGroup from '@/components/common/ActionButtonGroup.vue'
import EmptyState from '@/components/EmptyState.vue'
import { useCamerasStore } from '@/stores/cameras'

const { t } = useI18n()
const camerasStore = useCamerasStore()

const schedules = ref([])
const cameras = ref([])
const loading = ref(false)
const dialog = ref(false)
const isEdit = ref(false)
const submitting = ref(false)

const form = ref({ camera_mac: '', name: '', cron_expr: '0 2 * * *', segment_duration: 1800, enabled: true, preset_id: null, overrides: {} })
const editId = ref(null)
const showOverrides = ref(false)
const dialogTitle = ref('')
const submitText = ref('')

onMounted(async () => {
  const { data } = await listCameras()
  cameras.value = data
  fetch()
})

watch(() => form.value.camera_mac, async (newMac) => {
  if (newMac) {
    const mac = newMac
    try {
      await camerasStore.loadPresets(mac)
    } catch (e) {
      console.warn('Failed to load presets for camera:', mac, e.message)
    }
    const presets = camerasStore.presets[mac] || []
    if (presets.length > 0) {
      const defaultPreset = presets.find(p => p.id === camerasStore.defaultPresetId[mac]) || presets[0]
      form.value.preset_id = defaultPreset.id
    } else {
      form.value.preset_id = null
    }
  } else {
    form.value.preset_id = null
  }
  form.value.overrides = {}
  showOverrides.value = false
})

async function fetch() {
  loading.value = true
  try {
    const { data } = await listSchedules()
    schedules.value = data
  } finally {
    loading.value = false
  }
}

function openAdd() {
  isEdit.value = false
  editId.value = null
  form.value = { camera_mac: '', name: '', cron_expr: '0 2 * * *', segment_duration: 1800, enabled: true, preset_id: null, overrides: {} }
  showOverrides.value = false
  dialogTitle.value = t('schedule.newSchedule')
  submitText.value = t('common.create')
  dialog.value = true
}

async function openEdit(row) {
  isEdit.value = true
  editId.value = row.id
  try {
    await camerasStore.loadPresets(row.camera_mac)
  } catch (e) {
    console.warn('Failed to load presets for camera:', row.camera_mac, e.message)
  }
  form.value = { camera_mac: row.camera_mac, name: row.name || '', cron_expr: row.cron_expr, segment_duration: row.segment_duration, enabled: row.enabled, preset_id: row.preset_id || null, overrides: row.overrides || {} }
  showOverrides.value = !!(row.overrides && Object.keys(row.overrides).length > 0)
  dialogTitle.value = t('schedule.editSchedule')
  submitText.value = t('common.save')
  dialog.value = true
}

async function handleSubmit() {
  if (submitting.value) return
  submitting.value = true
  try {
    const payload = { ...form.value }
    if (!payload.preset_id) delete payload.preset_id
    if (!payload.overrides || Object.keys(payload.overrides).length === 0) delete payload.overrides
    if (isEdit.value) {
      await updateSchedule(editId.value, payload)
      ElMessage.success(t('schedule.updated'))
    } else {
      await createSchedule(payload)
      ElMessage.success(t('schedule.created'))
    }
    dialog.value = false
    fetch()
  } catch (e) {
    ElMessage.error(e.response?.data?.error?.message || t('common.operationFailed'))
  } finally {
    submitting.value = false
  }
}

async function toggleEnabled(row) {
  await updateSchedule(row.id, { enabled: !row.enabled })
  fetch()
}

async function handleDelete(row) {
  await ElMessageBox.confirm(t('schedule.deleteConfirm', { name: row.name || row.cron_expr }), t('common.confirmDelete'), { type: 'warning' })
  await deleteSchedule(row.id)
  ElMessage.success(t('schedule.deleted'))
  fetch()
}
</script>

<template>
  <div class="schedule-view">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">{{ $t('schedule.title') }}</h2>
      </div>
      <el-button type="primary" class="add-btn" @click="openAdd">
        <Plus />
        {{ $t('schedule.newSchedule') }}
      </el-button>
    </div>

    <div v-if="loading" class="table-loading">
      <el-skeleton :rows="4" animated class="table-loading-skeleton" />
    </div>
    <div v-else-if="schedules.length > 0" class="table-content">
    <el-table :data="schedules" style="width: 100%" row-key="id">
      <el-table-column prop="name" :label="$t('schedule.scheduleName')" min-width="160">
        <template #default="{ row }">
          <div class="name-cell">
            <span class="cell-name">{{ row.name || $t('schedule.unnamed') }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="camera_mac" :label="$t('schedule.cameraMac')" width="150">
        <template #default="{ row }">
          <span class="cell-mono">{{ row.camera_mac }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="cron_expr" :label="$t('schedule.triggerTime')" width="140">
        <template #default="{ row }">
          <div class="cron-cell">
            <Clock class="cron-icon" />
            <span>{{ row.cron_expr }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column :label="$t('schedule.segmentDuration')" width="110">
        <template #default="{ row }">
          <span class="cell-secondary">{{ Math.floor(row.segment_duration / 60) }} {{ $t('schedule.segmentUnit') }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('schedule.status')" width="80" align="center">
        <template #default="{ row }">
          <el-switch :model-value="row.enabled" @change="toggleEnabled(row)" />
        </template>
      </el-table-column>
      <el-table-column :label="$t('schedule.actions')" width="100" align="center" fixed="right">
        <template #default="{ row }">
          <ActionButtonGroup
            :actions="[
              { icon: Edit, tooltip: $t('common.edit'), onClick: () => openEdit(row) },
              { icon: Delete, tooltip: $t('common.delete'), danger: true, onClick: () => handleDelete(row) },
            ]"
          />
        </template>
      </el-table-column>
    </el-table>
    </div>
    <div v-else class="schedule-empty">
      <EmptyState
        icon="schedule"
        :title="$t('common.empty.schedules.title')"
        :description="$t('common.empty.schedules.description')"
        :action-label="$t('common.empty.schedules.action')"
        @action="openAdd"
      />
    </div>

    <el-dialog
      v-model="dialog"
      :title="dialogTitle"
      width="720px"
      class="schedule-dialog"
      :close-on-click-modal="false"
    >
      <el-form :model="form" label-position="top" class="schedule-form">
        <div class="form-section">
          <div class="section-title">
            <Calendar />
            {{ $t('schedule.basicInfo') }}
          </div>
          <el-form-item :label="$t('schedule.cameraMac')">
            <el-select v-model="form.camera_mac" :placeholder="$t('schedule.selectCamera')" style="width: 100%">
              <el-option
                v-for="c in cameras"
                :key="c.device_mac"
                :label="c.onvif_host || c.device_mac"
                :value="c.device_mac"
              />
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('schedule.scheduleName')">
            <el-input v-model="form.name" :placeholder="$t('schedule.namePlaceholder')" />
          </el-form-item>
        </div>

        <div class="form-section">
          <div class="section-title">
            <Clock />
            {{ $t('schedule.scheduleTiming') }}
          </div>
          <el-form-item :label="$t('schedule.triggerTime')" class="cron-field">
            <CronSelector v-model="form.cron_expr" />
          </el-form-item>
          <el-form-item :label="$t('schedule.segmentLabel')">
            <el-input-number v-model="form.segment_duration" :min="60" :step="300" style="width: 100%" />
          </el-form-item>
        </div>

        <div class="form-section">
          <div class="section-title">{{ $t('schedule.preset') }}</div>
          <el-form-item :label="$t('schedule.preset')">
            <el-select v-model="form.preset_id" :placeholder="$t('schedule.selectPreset')" style="width: 100%" clearable>
              <el-option
                v-for="p in (camerasStore.presets[form.camera_mac] || [])"
                :key="p.id"
                :label="p.name"
                :value="p.id"
              />
            </el-select>
          </el-form-item>
        </div>

        <div class="form-section">
          <el-form-item class="override-toggle">
            <el-button text type="primary" @click="showOverrides = !showOverrides">
              {{ showOverrides ? $t('schedule.hideOverrides') : $t('schedule.showOverrides') }}
              <span class="toggle-arrow" :class="{ open: showOverrides }">
                <svg viewBox="0 0 16 16" fill="none"><path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              </span>
            </el-button>
          </el-form-item>
          <template v-if="showOverrides">
            <div class="override-grid">
              <el-form-item :label="$t('schedule.resolution')">
                <el-select v-model="form.overrides.resolution" style="width: 100%" clearable>
                  <el-option value="1920x1080" :label="$t('schedule.res1920x1080')" />
                  <el-option value="1280x720" :label="$t('schedule.res1280x720')" />
                  <el-option value="640x360" :label="$t('schedule.res640x360')" />
                </el-select>
              </el-form-item>
              <el-form-item :label="$t('schedule.bitrate')">
                <el-input-number v-model="form.overrides.bitrate" :min="256" :max="20000" :step="256" style="width: 100%" clearable :placeholder="$t('schedule.bitratePlaceholder')" />
              </el-form-item>
              <el-form-item :label="$t('schedule.frameRate')">
                <el-input-number v-model="form.overrides.frame_rate" :min="5" :max="60" style="width: 100%" clearable :placeholder="$t('schedule.frameRatePlaceholder')" />
              </el-form-item>
            </div>
          </template>
        </div>

        <el-form-item :label="$t('schedule.enabled')" class="enabled-row">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialog = false">{{ $t('schedule.cancel') }}</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">{{ submitText }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* ── Page header ─────────────────────────────── */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: -0.02em;
  margin: 0 0 2px;
}

.add-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 500;
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-text-inverse);
  height: 32px;
  transition: all var(--duration-fast) ease-out;
}

.add-btn:hover {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
}

/* ── Table ───────────────────────────────────── */
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
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

:deep(.el-table__body td.el-table__cell) {
  padding: 10px 0;
}

/* Cell content */
.name-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cell-name {
  font-weight: 600;
  color: var(--color-text-primary);
  font-size: 13px;
}

.cell-mono {
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  color: var(--color-text-secondary);
}

.cell-secondary {
  font-size: 13px;
  color: var(--color-text-muted);
}

.cron-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--color-text-secondary);
}

.cron-icon {
  width: 14px;
  height: 14px;
  color: var(--color-primary);
}

/* Action buttons */
.action-group {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.action-btn {
  --el-button-bg-color: transparent;
  --el-button-border-color: transparent;
  --el-button-hover-bg-color: var(--color-surface-overlay);
  --el-button-hover-border-color: transparent;
  --el-button-hover-text-color: var(--color-text-primary);
  --el-button-active-bg-color: var(--color-surface);
  --el-button-active-border-color: transparent;
  height: 30px;
  width: 30px;
  padding: 4px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  transition: all var(--transition-fast);
}

.action-btn--danger {
  --el-button-hover-bg-color: rgba(239, 68, 68, 0.12);
  --el-button-hover-text-color: var(--color-error);
  --el-button-active-bg-color: rgba(239, 68, 68, 0.18);
}

.action-btn:hover {
  transform: scale(1.05);
}

/* ── Loading skeleton ──────────────────────── */
.table-loading {
  display: block;
  padding: var(--space-3) 0;
  border-radius: var(--radius-md);
  overflow: hidden;
}

.table-loading-skeleton :deep(.el-skeleton__item) {
  height: 54px;
  margin-bottom: var(--space-2);
  border-radius: var(--radius-sm);
}

.table-loading-skeleton :deep(.el-skeleton__item:last-child) {
  margin-bottom: 0;
}

/* ── Empty state ───────────────────────────── */
.schedule-empty {
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-lg);
  background: transparent;
  animation: fade-up 400ms ease both;
}

/* ── Table entry animation ──────────────────── */
.table-content {
  animation: fade-up 400ms ease both;
}

@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ── Dialog ──────────────────────────────────── */
.schedule-dialog {
  border-radius: var(--radius-lg) !important;
}

/* ── Form ───────────────────────────────────── */
.schedule-form {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.form-section {
  padding: 16px 0;
  border-bottom: 1px solid var(--color-border-subtle, var(--color-border));
}

.form-section:last-of-type {
  border-bottom: none;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 12px;
}

.section-title svg,
.section-title .el-icon {
  width: 14px;
  height: 14px;
  color: var(--color-primary);
}

:deep(.el-form-item) {
  margin-bottom: 14px;
}

:deep(.el-form-item:last-child) {
  margin-bottom: 0;
}

:deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
}

:deep(.el-select .el-input__wrapper) {
  border-radius: var(--radius-sm);
}

/* Override section */
.override-toggle {
  margin-bottom: 12px;
}

.toggle-arrow {
  display: inline-flex;
  align-items: center;
  margin-left: 4px;
  transition: transform var(--transition-fast);
}

.toggle-arrow svg {
  width: 14px;
  height: 14px;
}

.toggle-arrow.open {
  transform: rotate(180deg);
}

.override-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 16px;
  background: var(--color-surface);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  animation: fade-up 200ms ease both;
}

/* Enabled row */
.enabled-row {
  display: flex;
  align-items: center;
  padding-top: 8px;
}

.enabled-row :deep(.el-form-item__content) {
  justify-content: flex-end;
}

/* ── Dialog transitions ──────────────────────── */
.el-dialog {
  animation: dialog-enter 300ms cubic-bezier(0.34, 1.56, 0.64, 1) both;
}

@keyframes dialog-enter {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(16px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
</style>
