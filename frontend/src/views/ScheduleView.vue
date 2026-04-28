<script setup>
import { ref, onMounted } from 'vue'
import { listSchedules, createSchedule, updateSchedule, deleteSchedule } from '@/api/schedules'
import { listCameras } from '@/api/cameras'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

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
      ElMessage.success('已更新')
    } else {
      await createSchedule(form.value)
      ElMessage.success('已创建')
    }
    dialog.value = false
    fetch()
  } catch (e) {
    ElMessage.error(e.response?.data?.error?.message || '操作失败')
  }
}

async function toggleEnabled(row) {
  await updateSchedule(row.id, { enabled: !row.enabled })
  fetch()
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除计划「${row.name || row.cron_expr}」？`, '确认删除', { type: 'warning' })
  await deleteSchedule(row.id)
  ElMessage.success('已删除')
  fetch()
}
</script>

<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">录制计划</h2>
      <el-button type="primary" :icon="Plus" @click="openAdd">新建计划</el-button>
    </div>

    <el-table v-loading="loading" :data="schedules" stripe border>
      <el-table-column prop="name" label="计划名称" min-width="120">
        <template #default="{ row }">{{ row.name || '(未命名)' }}</template>
      </el-table-column>
      <el-table-column prop="camera_mac" label="摄像头 MAC" width="160" />
      <el-table-column prop="cron_expr" label="Cron 表达式" width="150" />
      <el-table-column label="分段时长" width="120">
        <template #default="{ row }">{{ Math.floor(row.segment_duration / 60) }} 分钟</template>
      </el-table-column>
      <el-table-column label="状态" width="90" align="center">
        <template #default="{ row }">
          <el-switch :model-value="row.enabled" @change="toggleEnabled(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" align="center">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="isEdit ? '编辑计划' : '新建计划'" width="480px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="摄像头">
          <el-select v-model="form.camera_mac" placeholder="选择摄像头" style="width: 100%">
            <el-option
              v-for="c in cameras"
              :key="c.device_mac"
              :label="c.onvif_host"
              :value="c.device_mac"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="计划名称">
          <el-input v-model="form.name" placeholder="如：夜间录制" />
        </el-form-item>
        <el-form-item label="Cron 表达式">
          <el-input v-model="form.cron_expr" placeholder="分 时 日 月 周，如 0 2 * * *" />
          <div class="cron-hint">格式：分 小时 日 月 周几（5 字段）</div>
        </el-form-item>
        <el-form-item label="分段时长(秒)">
          <el-input-number v-model="form.segment_duration" :min="60" :step="300" />
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">{{ isEdit ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.cron-hint {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 4px;
}
</style>
