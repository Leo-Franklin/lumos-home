<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { listSchedules, createSchedule, updateSchedule, deleteSchedule } from '@/api/schedules'
import { listCameras } from '@/api/cameras'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Clock } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import CronSelector from '@/components/CronSelector.vue'
import ActionButtonGroup from '@/components/common/ActionButtonGroup.vue'
import EmptyState from '@/components/EmptyState.vue'
import RecordingPresetPicker from '@/components/recording/RecordingPresetPicker.vue'
import RecordingParamOverrides from '@/components/recording/RecordingParamOverrides.vue'
import { useCamerasStore } from '@/stores/cameras'
import { useApiError } from '@/composables/useApiError'
import { useRecordingParams } from '@/composables/useRecordingParams'
import {
  emptyOverrides,
  normalizeOverrides,
  buildOverridesPayload,
  SEGMENT_MIN,
  SEGMENT_MAX,
} from '@/constants/recordingParams'

const { t } = useI18n()
const handleError = useApiError()
const camerasStore = useCamerasStore()
const { segmentQuickOptions } = useRecordingParams()

const schedules = ref([])
const cameras = ref([])
const loading = ref(false)
const dialog = ref(false)
const isEdit = ref(false)
const submitting = ref(false)

const form = ref({
  camera_mac: '',
  name: '',
  cron_expr: '0 2 * * *',
  segment_duration: 1800,
  enabled: true,
  preset_id: null,
  overrides: emptyOverrides(),
})
const editId = ref(null)
const overridesExpanded = ref(false)
const dialogTitle = ref('')
const submitText = ref('')

const currentPresets = computed(() => {
  const mac = form.value.camera_mac
  return mac ? camerasStore.presets[mac] || [] : []
})

const formHint = computed(() =>
  isEdit.value ? t('schedule.formHintEdit') : t('schedule.formHintNew'),
)

function cameraLabel(c) {
  const host = c.onvif_host || c.device_mac
  return host === c.device_mac ? host : `${host} · ${c.device_mac}`
}

onMounted(async () => {
  const { data } = await listCameras()
  cameras.value = data
  fetch()
})

watch(
  () => form.value.camera_mac,
  async (newMac) => {
    if (newMac) {
      const mac = newMac
      try {
        await camerasStore.loadPresets(mac)
      } catch {
        // Presets are optional; the form remains usable without them.
      }
      const presets = camerasStore.presets[mac] || []
      if (presets.length > 0) {
        const defaultPreset =
          presets.find((p) => p.id === camerasStore.defaultPresetId[mac]) || presets[0]
        form.value.preset_id = defaultPreset.id
      } else {
        form.value.preset_id = null
      }
    } else {
      form.value.preset_id = null
    }
    form.value.overrides = emptyOverrides()
    overridesExpanded.value = false
  },
)

watch(
  () => form.value.preset_id,
  (id) => {
    if (!id) return
    const preset = currentPresets.value.find((p) => p.id === id)
    if (preset) form.value.segment_duration = preset.segment_duration
  },
)

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
  const defaultCameraMac = cameras.value.length === 1 ? cameras.value[0].device_mac : ''
  form.value = {
    camera_mac: '',
    name: '',
    cron_expr: '0 2 * * *',
    segment_duration: 1800,
    enabled: true,
    preset_id: null,
    overrides: emptyOverrides(),
  }
  overridesExpanded.value = false
  dialogTitle.value = t('schedule.newSchedule')
  submitText.value = t('common.create')
  dialog.value = true
  if (defaultCameraMac) {
    form.value.camera_mac = defaultCameraMac
  }
}

async function openEdit(row) {
  isEdit.value = true
  editId.value = row.id
  try {
    await camerasStore.loadPresets(row.camera_mac)
  } catch {
    // Presets are optional; keep the saved preset_id when the list cannot be loaded.
  }
  form.value = {
    camera_mac: row.camera_mac,
    name: row.name || '',
    cron_expr: row.cron_expr,
    segment_duration: row.segment_duration,
    enabled: row.enabled,
    preset_id: row.preset_id || null,
    overrides: normalizeOverrides(row.overrides),
  }
  overridesExpanded.value = !!(row.overrides && Object.keys(row.overrides).length > 0)
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
    const overrides = buildOverridesPayload(payload.overrides, { target: 'schedule' })
    if (Object.keys(overrides).length) payload.overrides = overrides
    else delete payload.overrides
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
    handleError(e, 'common.operationFailed')
  } finally {
    submitting.value = false
  }
}

async function toggleEnabled(row) {
  await updateSchedule(row.id, { enabled: !row.enabled })
  fetch()
}

async function handleDelete(row) {
  await ElMessageBox.confirm(
    t('schedule.deleteConfirm', { name: row.name || row.cron_expr }),
    t('common.confirmDelete'),
    { type: 'warning' },
  )
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
            <span class="cell-secondary"
              >{{ Math.floor(row.segment_duration / 60) }} {{ $t('schedule.segmentUnit') }}</span
            >
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
                {
                  icon: Edit,
                  tooltip: $t('common.edit'),
                  ariaLabel: $t('common.edit'),
                  onClick: () => openEdit(row),
                },
                {
                  icon: Delete,
                  tooltip: $t('common.delete'),
                  ariaLabel: $t('common.delete'),
                  danger: true,
                  onClick: () => handleDelete(row),
                },
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
      width="640px"
      class="schedule-dialog"
      :close-on-click-modal="false"
      align-center
      destroy-on-close
    >
      <template #header>
        <div class="dialog-header">
          <span class="dialog-title">{{ dialogTitle }}</span>
          <span class="dialog-hint">{{ formHint }}</span>
        </div>
      </template>

      <el-form :model="form" label-position="top" class="schedule-form" @submit.prevent>
        <div class="form-row">
          <el-form-item :label="$t('schedule.cameraLabel')" class="form-row__item">
            <el-select
              v-model="form.camera_mac"
              :placeholder="$t('schedule.selectCamera')"
              style="width: 100%"
            >
              <el-option
                v-for="c in cameras"
                :key="c.device_mac"
                :label="cameraLabel(c)"
                :value="c.device_mac"
              />
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('schedule.scheduleName')" class="form-row__item">
            <el-input v-model="form.name" :placeholder="$t('schedule.namePlaceholder')" />
          </el-form-item>
        </div>

        <el-divider content-position="left">{{ $t('schedule.scheduleTiming') }}</el-divider>

        <el-form-item :label="$t('schedule.triggerTime')" class="cron-field">
          <CronSelector v-model="form.cron_expr" />
        </el-form-item>

        <el-divider content-position="left">{{ $t('schedule.recordingSettings') }}</el-divider>

        <div v-if="!form.camera_mac" class="recording-placeholder">
          {{ $t('recording.selectCameraFirst') }}
        </div>
        <template v-else>
          <RecordingPresetPicker
            v-model="form.preset_id"
            :presets="currentPresets"
            :mode="currentPresets.length ? 'cards' : 'select'"
            :clearable="true"
            :show-cards-hint="false"
            :hint="currentPresets.length ? '' : $t('recording.noPresetsAvailable')"
          />

          <el-form-item v-if="!form.preset_id" class="segment-field">
            <template #label>
              <span class="field-label-with-hint">
                {{ $t('schedule.segmentLabel') }}
                <span class="field-hint">{{ $t('schedule.segmentFallbackHint') }}</span>
              </span>
            </template>
            <div class="segment-picks">
              <el-button
                v-for="opt in segmentQuickOptions"
                :key="opt.value"
                size="small"
                :type="form.segment_duration === opt.value ? 'primary' : 'default'"
                :plain="form.segment_duration !== opt.value"
                @click="form.segment_duration = opt.value"
              >
                {{ opt.label }}
              </el-button>
            </div>
            <el-input-number
              v-model="form.segment_duration"
              :min="SEGMENT_MIN"
              :max="SEGMENT_MAX"
              :step="60"
              controls-position="right"
              class="segment-input"
            />
          </el-form-item>

          <RecordingParamOverrides
            v-model="form.overrides"
            collapsible
            :show-segment="false"
            label-position="top"
            :default-expanded="overridesExpanded"
          />
        </template>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <div class="footer-left">
            <span class="enabled-label">{{ $t('schedule.enabled') }}</span>
            <el-switch v-model="form.enabled" />
          </div>
          <div class="footer-actions">
            <el-button @click="dialog = false">{{ $t('schedule.cancel') }}</el-button>
            <el-button type="primary" :loading="submitting" @click="handleSubmit">
              {{ submitText }}
            </el-button>
          </div>
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

.dialog-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-right: 24px;
}

.dialog-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  line-height: 1.3;
}

.dialog-hint {
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.45;
}

.recording-placeholder {
  font-size: 13px;
  color: var(--color-text-muted);
  padding: 8px 0 4px;
}

.schedule-form :deep(.picker-cards) {
  margin-bottom: 12px;
}

/* ── Form ───────────────────────────────────── */
.schedule-form {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding-right: 8px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.form-row__item {
  min-width: 0;
}

.schedule-form :deep(.el-divider) {
  margin: 4px 0 16px;
}

.schedule-form :deep(.el-divider__text) {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  background: var(--color-surface-overlay);
  padding: 0 8px;
}

:deep(.el-form-item) {
  margin-bottom: 16px;
}

:deep(.el-form-item:last-child) {
  margin-bottom: 0;
}

:deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
  line-height: 1.4;
}

.cron-field :deep(.el-form-item__content) {
  line-height: 1;
}

.field-label-with-hint {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.field-hint {
  font-size: 11px;
  font-weight: 400;
  color: var(--color-text-muted);
}

.segment-picks {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.segment-input {
  width: 160px;
}

.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.enabled-label {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.footer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
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
