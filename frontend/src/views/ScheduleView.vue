<script setup>
import { ref, onMounted } from 'vue'
import { listSchedules, createSchedule, updateSchedule, deleteSchedule } from '@/api/schedules'
import { listCameras } from '@/api/cameras'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import CronSelector from '@/components/CronSelector.vue'

const { t } = useI18n()

const schedules = ref([])
const cameras = ref([])
const loading = ref(false)
const dialog = ref(false)
const isEdit = ref(false)

const form = ref({ camera_mac: '', name: '', cron_expr: '0 2 * * *', segment_duration: 1800, enabled: true })
const editId = ref(null)

onMounted(async () => {
  const { data } = await listCameras()
  cameras.value = data
  fetch()
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
  form.value = { camera_mac: '', name: '', cron_expr: '0 2 * * *', segment_duration: 1800, enabled: true }
  editId.value = null
  dialog.value = true
}

function openEdit(row) {
  isEdit.value = true
  editId.value = row.id
  form.value = { camera_mac: row.camera_mac, name: row.name || '', cron_expr: row.cron_expr, segment_duration: row.segment_duration, enabled: row.enabled }
  dialog.value = true
}

async function handleSubmit() {
  try {
    if (isEdit.value) {
      await updateSchedule(editId.value, form.value)
      ElMessage.success(t('schedule.updated'))
    } else {
      await createSchedule(form.value)
      ElMessage.success(t('schedule.created'))
    }
    dialog.value = false
    fetch()
  } catch (e) {
    ElMessage.error(e.response?.data?.error?.message || t('common.operationFailed'))
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
  <div>
    <div class="page-header">
      <h2 class="page-title">{{ $t('schedule.title') }}</h2>
      <el-button type="primary" :icon="Plus" @click="openAdd">{{ $t('schedule.newSchedule') }}</el-button>
    </div>

    <el-table v-loading="loading" :data="schedules" style="width: 100%">
      <el-table-column prop="name" :label="$t('schedule.scheduleName')" min-width="120">
        <template #default="{ row }">{{ row.name || $t('schedule.unnamed') }}</template>
      </el-table-column>
      <el-table-column prop="camera_mac" :label="$t('schedule.cameraMac')" width="160" />
      <el-table-column prop="cron_expr" :label="$t('schedule.cronExpr')" width="150" />
      <el-table-column :label="$t('schedule.segmentDuration')" width="120">
        <template #default="{ row }">{{ Math.floor(row.segment_duration / 60) }}{{ $t('schedule.segmentUnit') }}</template>
      </el-table-column>
      <el-table-column :label="$t('schedule.status')" width="90" align="center">
        <template #default="{ row }">
          <el-switch :model-value="row.enabled" @change="toggleEnabled(row)" />
        </template>
      </el-table-column>
      <el-table-column :label="$t('schedule.actions')" width="120" align="center">
        <template #default="{ row }">
          <div class="action-group">
            <el-tooltip :content="$t('common.edit')" :show-after="400">
              <el-button class="action-btn" size="small" :icon="Edit" @click="openEdit(row)" />
            </el-tooltip>
            <el-tooltip :content="$t('common.delete')" :show-after="400">
              <el-button class="action-btn action-btn--danger" size="small" :icon="Delete" @click="handleDelete(row)" />
            </el-tooltip>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="isEdit ? $t('schedule.editSchedule') : $t('schedule.newSchedule')" width="680px">
      <el-form :model="form" label-width="110px">
        <el-form-item :label="$t('schedule.cameraMac')">
          <el-select v-model="form.camera_mac" :placeholder="$t('schedule.selectCamera')" style="width: 100%">
            <el-option
              v-for="c in cameras"
              :key="c.device_mac"
              :label="c.onvif_host"
              :value="c.device_mac"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('schedule.scheduleName')">
          <el-input v-model="form.name" :placeholder="$t('schedule.namePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('schedule.triggerTime')" style="width: 100%">
          <CronSelector v-model="form.cron_expr" />
        </el-form-item>
        <el-form-item :label="$t('schedule.segmentLabel')">
          <el-input-number v-model="form.segment_duration" :min="60" :step="300" />
        </el-form-item>
        <el-form-item :label="$t('schedule.enabled')">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">{{ $t('schedule.cancel') }}</el-button>
        <el-button type="primary" @click="handleSubmit">{{ isEdit ? $t('common.save') : $t('common.create') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* ── Table styling ──────────────────────────── */
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
}

:deep(.el-table__body td.el-table__cell) {
  padding: 10px 0;
}

:deep(.el-table__inner-wrapper::before) {
  display: none;
}

/* Action buttons */
.action-group {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1px;
}

.action-btn {
  --el-button-bg-color: transparent;
  --el-button-border-color: transparent;
  --el-button-hover-bg-color: var(--color-surface-raised);
  --el-button-hover-border-color: transparent;
  --el-button-hover-text-color: var(--color-text-primary);
  --el-button-active-bg-color: var(--color-surface-overlay);
  --el-button-active-border-color: transparent;
  height: 28px;
  width: 28px;
  padding: 3px;
  border-radius: 5px;
  font-size: 15px;
  transition: background var(--duration-fast) ease-out,
              color var(--duration-fast) ease-out;
}

.action-btn--danger {
  --el-button-hover-bg-color: rgba(240, 82, 82, 0.1);
  --el-button-hover-text-color: var(--color-error);
  --el-button-active-bg-color: rgba(240, 82, 82, 0.15);
}
</style>
