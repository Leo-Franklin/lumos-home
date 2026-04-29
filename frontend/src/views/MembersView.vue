<script setup>
import { ref, onMounted } from 'vue'
import { useMembersStore } from '@/stores/members'
import { listDevices } from '@/api/devices'
import { listCameras } from '@/api/cameras'
import {
  createMember, updateMember, deleteMember,
  listMemberDevices, bindDevice, unbindDevice,
  listPresenceLogs, getMemberStats,
} from '@/api/members'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

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
      ElMessage.success('已更新')
    } else {
      await createMember(payload)
      ElMessage.success('已创建')
    }
    memberDialog.value = false
    membersStore.fetchMembers()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleDeleteMember(row) {
  await ElMessageBox.confirm(`确定删除成员「${row.name}」？关联数据也会一并删除。`, '确认删除', { type: 'warning' })
  await deleteMember(row.id)
  ElMessage.success('已删除')
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
    ElMessage.success('已绑定')
    bindForm.value = { mac: '', label: '' }
    loadBoundDevices(currentMember.value.id)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '绑定失败')
  }
}

async function handleUnbind(mac) {
  await unbindDevice(currentMember.value.id, mac)
  ElMessage.success('已解绑')
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
    ElMessage.error(e.response?.data?.detail || '统计加载失败')
  } finally {
    statsLoading.value = false
  }
}

function statsDailyMax() {
  return Math.max(...(statsData.value?.daily || []).map((d) => d.minutes), 1)
}

function fmtMinutes(m) {
  if (!m) return '0 分钟'
  const h = Math.floor(m / 60), min = m % 60
  return h > 0 ? `${h} 小时 ${min} 分钟` : `${min} 分钟`
}

// ── Helpers ────────────────────────────────────────────────
function fmtTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
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
      <h2 class="page-title">家庭成员</h2>
      <el-button type="primary" :icon="Plus" @click="openAddMember">添加成员</el-button>
    </div>

    <el-table v-loading="membersStore.loading" :data="membersStore.items" stripe border>
      <el-table-column label="姓名" min-width="120">
        <template #default="{ row }">
          <div class="member-name-cell">
            <el-avatar v-if="row.avatar_url" :src="row.avatar_url" :size="28" />
            <el-avatar v-else :size="28">{{ row.name.charAt(0) }}</el-avatar>
            <span>{{ row.name }}</span>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.is_home ? 'success' : 'info'" size="small">
            {{ row.is_home ? '在家' : '外出' }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="最近到家" width="180">
        <template #default="{ row }">{{ fmtTime(row.last_arrived_at) }}</template>
      </el-table-column>

      <el-table-column label="最近离家" width="180">
        <template #default="{ row }">{{ fmtTime(row.last_left_at) }}</template>
      </el-table-column>

      <el-table-column label="Webhook" min-width="160">
        <template #default="{ row }">
          <span class="text-muted">{{ row.webhook_url || '—' }}</span>
        </template>
      </el-table-column>

      <el-table-column label="自动录制" min-width="120">
        <template #default="{ row }">
          <span v-if="row.auto_record_cameras?.length" class="text-muted">
            {{ row.auto_record_cameras.length }} 台
          </span>
          <span v-else class="text-muted">—</span>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="280" align="center">
        <template #default="{ row }">
          <el-button size="small" @click="openDevices(row)">绑定设备</el-button>
          <el-button size="small" @click="openLogs(row)">日志</el-button>
          <el-button size="small" @click="openStats(row)">统计</el-button>
          <el-button size="small" @click="openEditMember(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDeleteMember(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Member create/edit dialog -->
    <el-dialog v-model="memberDialog" :title="isEditMember ? '编辑成员' : '添加成员'" width="460px">
      <el-form :model="memberForm" label-width="110px">
        <el-form-item label="姓名" required>
          <el-input v-model="memberForm.name" placeholder="如：张三" />
        </el-form-item>
        <el-form-item label="头像 URL">
          <el-input v-model="memberForm.avatar_url" placeholder="可选" />
        </el-form-item>
        <el-form-item label="Webhook">
          <el-input v-model="memberForm.webhook_url" placeholder="到家/离家时推送，可选" />
        </el-form-item>
        <el-form-item label="自动录制摄像头">
          <el-select
            v-model="memberForm.auto_record_cameras"
            multiple
            clearable
            placeholder="到家时自动启动录制（可选）"
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
        <el-button @click="memberDialog = false">取消</el-button>
        <el-button type="primary" @click="submitMember">{{ isEditMember ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>

    <!-- Bound devices dialog -->
    <el-dialog
      v-model="devicesDialog"
      :title="`绑定设备 — ${currentMember?.name}`"
      width="560px"
    >
      <div class="bind-row">
        <el-select
          v-model="bindForm.mac"
          placeholder="选择设备"
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
        <el-input v-model="bindForm.label" placeholder="备注（可选）" style="width: 130px" />
        <el-button type="primary" @click="handleBind">绑定</el-button>
      </div>

      <el-table v-loading="devicesLoading" :data="boundDevices" style="margin-top: 12px" border size="small">
        <el-table-column label="设备" min-width="160">
          <template #default="{ row }">{{ deviceLabel(row) }}</template>
        </el-table-column>
        <el-table-column prop="mac" label="MAC" width="150" />
        <el-table-column prop="label" label="备注" min-width="100">
          <template #default="{ row }">{{ row.label || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click="handleUnbind(row.mac)">解绑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- Presence logs dialog -->
    <el-dialog
      v-model="logsDialog"
      :title="`到家日志 — ${logsMember?.name}`"
      width="520px"
    >
      <el-table v-loading="logsLoading" :data="logs" border size="small">
        <el-table-column label="事件" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.event === 'arrived' ? 'success' : 'warning'" size="small">
              {{ row.event === 'arrived' ? '到家' : '离家' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="触发设备 MAC" min-width="150">
          <template #default="{ row }">{{ row.triggered_by_mac || '—' }}</template>
        </el-table-column>
        <el-table-column label="时间" min-width="170">
          <template #default="{ row }">{{ fmtTime(row.occurred_at) }}</template>
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
      :title="`在家统计 — ${statsMember?.name}`"
      width="560px"
      destroy-on-close
    >
      <div class="stats-toolbar">
        <el-radio-group v-model="statsRange" @change="fetchMemberStats(statsMember.id)">
          <el-radio-button value="7d">近 7 天</el-radio-button>
          <el-radio-button value="30d">近 30 天</el-radio-button>
        </el-radio-group>
        <span v-if="statsData" class="stats-total">
          累计在家：{{ fmtMinutes(statsData.total_minutes) }}
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
            :title="`${d.date}: ${fmtMinutes(d.minutes)}`"
          />
          <div class="daily-label">{{ d.date.slice(5) }}</div>
        </div>
        <div v-if="!statsData.daily?.length" class="empty-hint">暂无数据</div>
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
</style>
