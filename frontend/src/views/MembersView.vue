<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatDuration } from '@/composables/useFormatDuration'
import { useMembersStore } from '@/stores/members'
import { listDevices } from '@/api/devices'
import { listCameras } from '@/api/cameras'
import {
  createMember, updateMember, deleteMember,
  listMemberDevices, bindDevice, unbindDevice,
  listPresenceLogs, getMemberStats,
} from '@/api/members'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, Delete, Link, Document, DataAnalysis, Plus } from '@element-plus/icons-vue'

const { t } = useI18n()
const { formatDuration } = useFormatDuration()

const membersStore = useMembersStore()

// ── Devices pool for bind selector ────────────────────────
const allDevices = ref([])
const allCameras = ref([])

onMounted(async () => {
  await membersStore.fetchMembers()
  const [devRes, camRes] = await Promise.all([
    listDevices({ page: 1, page_size: 100 }),
    listCameras(),
  ])
  allDevices.value = devRes.data.items
  allCameras.value = camRes.data
})

// ── Member CRUD ────────────────────────────────────────────
const memberDialog = ref(false)
const isEditMember = ref(false)
const memberForm = ref({ name: '', avatar_url: '', webhook_url: '', auto_record_cameras: [] })
const editMemberId = ref(null)

function openAddMember() {
  isEditMember.value = false
  editMemberId.value = null
  memberForm.value = { name: '', avatar_url: '', webhook_url: '', auto_record_cameras: [] }
  memberDialog.value = true
}

function openEditMember(row) {
  isEditMember.value = true
  editMemberId.value = row.id
  memberForm.value = {
    name: row.name,
    avatar_url: row.avatar_url || '',
    webhook_url: row.webhook_url || '',
    auto_record_cameras: row.auto_record_cameras ? [...row.auto_record_cameras] : [],
  }
  memberDialog.value = true
}

async function submitMember() {
  try {
    const payload = {
      name: memberForm.value.name,
      avatar_url: memberForm.value.avatar_url || null,
      webhook_url: memberForm.value.webhook_url || null,
      auto_record_cameras: memberForm.value.auto_record_cameras,
    }
    if (isEditMember.value) {
      await updateMember(editMemberId.value, payload)
      ElMessage.success(t('members.updated'))
    } else {
      await createMember(payload)
      ElMessage.success(t('members.created'))
    }
    memberDialog.value = false
    membersStore.fetchMembers()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('common.operationFailed'))
  }
}

async function handleDeleteMember(row) {
  await ElMessageBox.confirm(t('members.deleteConfirm', { name: row.name }), t('common.confirmDelete'), { type: 'warning' })
  await deleteMember(row.id)
  ElMessage.success(t('members.deleted'))
  membersStore.fetchMembers()
}

// ── Bound Devices ──────────────────────────────────────────
const devicesDialog = ref(false)
const currentMember = ref(null)
const boundDevices = ref([])
const devicesLoading = ref(false)
const bindForm = ref({ mac: '', label: '' })

async function openDevices(member) {
  currentMember.value = member
  devicesDialog.value = true
  bindForm.value = { mac: '', label: '' }
  await loadBoundDevices(member.id)
}

async function loadBoundDevices(memberId) {
  devicesLoading.value = true
  try {
    const { data } = await listMemberDevices(memberId)
    boundDevices.value = data
  } finally {
    devicesLoading.value = false
  }
}

async function handleBind() {
  if (!bindForm.value.mac) return
  try {
    await bindDevice(currentMember.value.id, { mac: bindForm.value.mac, label: bindForm.value.label || null })
    ElMessage.success(t('members.bound'))
    bindForm.value = { mac: '', label: '' }
    loadBoundDevices(currentMember.value.id)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('members.bindFailed'))
  }
}

async function handleUnbind(mac) {
  await unbindDevice(currentMember.value.id, mac)
  ElMessage.success(t('members.unbound'))
  loadBoundDevices(currentMember.value.id)
}

// ── Presence Logs ──────────────────────────────────────────
const logsDialog = ref(false)
const logsMember = ref(null)
const logs = ref([])
const logsTotal = ref(0)
const logsPage = ref(1)
const logsLoading = ref(false)

async function openLogs(member) {
  logsMember.value = member
  logsPage.value = 1
  logsDialog.value = true
  await loadLogs(member.id)
}

async function loadLogs(memberId) {
  logsLoading.value = true
  try {
    const { data } = await listPresenceLogs(memberId, { page: logsPage.value, page_size: 20 })
    logs.value = data.items
    logsTotal.value = data.total
  } finally {
    logsLoading.value = false
  }
}

function handleLogsPageChange(p) {
  logsPage.value = p
  loadLogs(logsMember.value.id)
}

// ── Stats (C1) ─────────────────────────────────────────────
const statsDialog = ref(false)
const statsMember = ref(null)
const statsRange = ref('7d')
const statsData = ref(null)
const statsLoading = ref(false)

async function openStats(member) {
  statsMember.value = member
  statsRange.value = '7d'
  statsData.value = null
  statsDialog.value = true
  await fetchMemberStats(member.id)
}

async function fetchMemberStats(id) {
  statsLoading.value = true
  try {
    const { data } = await getMemberStats(id, { range: statsRange.value })
    statsData.value = data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('members.statsFailed'))
  } finally {
    statsLoading.value = false
  }
}

// ── Helpers ────────────────────────────────────────────────
function statsDailyMax() {
  return Math.max(...(statsData.value?.daily || []).map((d) => d.minutes), 1)
}

function deviceLabel(d) {
  return d.device_info?.alias || d.device_info?.hostname || d.mac
}

const unboundDevices = () =>
  allDevices.value.filter((d) => !boundDevices.value.some((b) => b.mac === d.mac))
</script>

<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">{{ $t('members.title') }}</h2>
      <el-button type="primary" :icon="Plus" @click="openAddMember">{{ $t('members.addMember') }}</el-button>
    </div>

    <el-table v-loading="membersStore.loading" :data="membersStore.items" style="width: 100%">
      <el-table-column :label="$t('members.name')" min-width="120">
        <template #default="{ row }">
          <div class="member-name-cell">
            <el-avatar v-if="row.avatar_url" :src="row.avatar_url" :size="28" />
            <el-avatar v-else :size="28">{{ row.name.charAt(0) }}</el-avatar>
            <span>{{ row.name }}</span>
          </div>
        </template>
      </el-table-column>

      <el-table-column :label="$t('members.status')" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.is_home ? 'success' : 'info'" size="small">
            {{ row.is_home ? $t('members.home') : $t('members.away') }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column :label="$t('members.lastArrived')" width="180">
        <template #default="{ row }">{{ $d(row.last_arrived_at, 'short') }}</template>
      </el-table-column>

      <el-table-column :label="$t('members.lastLeft')" width="180">
        <template #default="{ row }">{{ $d(row.last_left_at, 'short') }}</template>
      </el-table-column>

      <el-table-column :label="$t('members.webhook')" min-width="160">
        <template #default="{ row }">
          <span class="text-muted">{{ row.webhook_url || '—' }}</span>
        </template>
      </el-table-column>

      <el-table-column :label="$t('members.autoRecord')" min-width="120">
        <template #default="{ row }">
          <span v-if="row.auto_record_cameras?.length" class="text-muted">
            {{ row.auto_record_cameras.length }} 台
          </span>
          <span v-else class="text-muted">—</span>
        </template>
      </el-table-column>

      <el-table-column :label="$t('members.actions')" width="200" align="center">
        <template #default="{ row }">
          <div class="action-group">
            <el-tooltip :content="$t('members.bindDevice')" :show-after="400">
              <el-button class="action-btn" size="small" :icon="Link" @click="openDevices(row)" />
            </el-tooltip>
            <el-tooltip :content="$t('members.logs')" :show-after="400">
              <el-button class="action-btn" size="small" :icon="Document" @click="openLogs(row)" />
            </el-tooltip>
            <el-tooltip :content="$t('members.stats')" :show-after="400">
              <el-button class="action-btn" size="small" :icon="DataAnalysis" @click="openStats(row)" />
            </el-tooltip>
            <el-tooltip :content="$t('common.edit')" :show-after="400">
              <el-button class="action-btn" size="small" :icon="Edit" @click="openEditMember(row)" />
            </el-tooltip>
            <el-tooltip :content="$t('common.delete')" :show-after="400">
              <el-button class="action-btn action-btn--danger" size="small" :icon="Delete" @click="handleDeleteMember(row)" />
            </el-tooltip>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- Member create/edit dialog -->
    <el-dialog v-model="memberDialog" :title="isEditMember ? $t('members.editMember') : $t('members.addMember')" width="460px">
      <el-form :model="memberForm" label-width="110px">
        <el-form-item :label="$t('members.name')" required>
          <el-input v-model="memberForm.name" :placeholder="$t('members.namePlaceholder')" />
        </el-form-item>
        <el-form-item label="头像 URL">
          <el-input v-model="memberForm.avatar_url" :placeholder="$t('members.avatarOptional')" />
        </el-form-item>
        <el-form-item :label="$t('members.webhook')">
          <el-input v-model="memberForm.webhook_url" :placeholder="$t('members.webhookPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('members.autoRecord')">
          <el-select
            v-model="memberForm.auto_record_cameras"
            multiple
            clearable
            :placeholder="$t('members.autoRecordPlaceholder')"
            style="width: 100%"
          >
            <el-option
              v-for="c in allCameras"
              :key="c.device_mac"
              :label="c.onvif_host"
              :value="c.device_mac"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="memberDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submitMember">{{ isEditMember ? $t('common.save') : $t('common.create') }}</el-button>
      </template>
    </el-dialog>

    <!-- Bound devices dialog -->
    <el-dialog
      v-model="devicesDialog"
      :title="$t('members.bindDevicesTitle', { name: currentMember?.name })"
      width="560px"
    >
      <div class="bind-row">
        <el-select
          v-model="bindForm.mac"
          :placeholder="$t('members.selectDevice')"
          filterable
          style="flex: 1"
        >
          <el-option
            v-for="d in unboundDevices()"
            :key="d.mac"
            :label="`${d.alias || d.hostname || d.mac} (${d.ip})`"
            :value="d.mac"
          />
        </el-select>
        <el-input v-model="bindForm.label" :placeholder="$t('members.noteOptional')" style="width: 130px" />
        <el-button type="primary" @click="handleBind">{{ $t('members.bindDevice') }}</el-button>
      </div>

      <el-table v-loading="devicesLoading" :data="boundDevices" style="margin-top: 12px" size="small">
        <el-table-column :label="$t('members.device')" min-width="160">
          <template #default="{ row }">{{ deviceLabel(row) }}</template>
        </el-table-column>
        <el-table-column prop="mac" :label="$t('members.mac')" width="150" />
        <el-table-column prop="label" :label="$t('members.note')" min-width="100">
          <template #default="{ row }">{{ row.label || '—' }}</template>
        </el-table-column>
        <el-table-column :label="$t('members.actions')" width="80" align="center">
          <template #default="{ row }">
          <el-tooltip :content="$t('members.unbind')" :show-after="400">
            <el-button class="action-btn action-btn--danger" size="small" :icon="Delete" @click="handleUnbind(row.mac)" />
          </el-tooltip>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- Presence logs dialog -->
    <el-dialog
      v-model="logsDialog"
      :title="$t('members.logsTitle', { name: logsMember?.name })"
      width="520px"
    >
      <el-table v-loading="logsLoading" :data="logs" size="small">
        <el-table-column :label="$t('members.event')" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.event === 'arrived' ? 'success' : 'warning'" size="small">
              {{ row.event === 'arrived' ? $t('members.arrived') : $t('members.left') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('members.triggeredBy')" min-width="150">
          <template #default="{ row }">{{ row.triggered_by_mac || '—' }}</template>
        </el-table-column>
        <el-table-column :label="$t('members.time')" min-width="170">
          <template #default="{ row }">{{ $d(row.occurred_at, 'short') }}</template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 12px; text-align: right">
        <el-pagination
          small
          layout="total, prev, pager, next"
          :total="logsTotal"
          :page-size="20"
          :current-page="logsPage"
          @current-change="handleLogsPageChange"
        />
      </div>
    </el-dialog>

    <!-- Stats dialog (C1) -->
    <el-dialog
      v-model="statsDialog"
      :title="$t('members.statsTitle', { name: statsMember?.name })"
      width="560px"
      destroy-on-close
    >
      <div class="stats-toolbar">
        <el-radio-group v-model="statsRange" @change="fetchMemberStats(statsMember.id)">
          <el-radio-button value="7d">{{ $t('members.recent7Days') }}</el-radio-button>
          <el-radio-button value="30d">{{ $t('members.recent30Days') }}</el-radio-button>
        </el-radio-group>
        <span v-if="statsData" class="stats-total">
          {{ $t('members.statsTotal', { duration: formatDuration(statsData.total_minutes * 60) }) }}
        </span>
      </div>

      <el-skeleton v-if="statsLoading" :rows="4" animated style="margin-top:12px" />

      <div v-if="statsData && !statsLoading" class="daily-chart">
        <div
          v-for="d in statsData.daily"
          :key="d.date"
          class="daily-bar-col"
        >
          <div
            class="daily-bar"
            :style="{ height: Math.max(4, (d.minutes / statsDailyMax()) * 80) + 'px' }"
            :title="`${d.date}: ${formatDuration(d.minutes * 60)}`"
          />
          <div class="daily-label">{{ d.date.slice(5) }}</div>
        </div>
        <div v-if="!statsData.daily?.length" class="empty-hint">{{ $t('members.noData') }}</div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.member-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bind-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.text-muted {
  font-size: 12px;
  color: var(--color-text-muted);
  word-break: break-all;
}

.stats-toolbar {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 16px;
}

.stats-total {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.daily-chart {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 100px;
  padding-bottom: 20px;
  overflow-x: auto;
}

.daily-bar-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 28px;
  flex: 1;
}

.daily-bar {
  width: 100%;
  background: var(--color-primary, #5e5ce6);
  border-radius: 2px 2px 0 0;
  cursor: default;
  transition: opacity 0.15s;
}

.daily-bar:hover { opacity: 0.75; }

.daily-label {
  font-size: 10px;
  color: var(--color-text-muted);
  margin-top: 4px;
  white-space: nowrap;
}

.empty-hint {
  font-size: 13px;
  color: var(--color-text-muted);
  margin: auto;
}

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
