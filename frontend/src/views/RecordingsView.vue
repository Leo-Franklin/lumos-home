<script setup>
import { ref, onMounted, watch } from 'vue'
import { listRecordings, deleteRecording, streamUrl, downloadUrl } from '@/api/recordings'
import { listCameras } from '@/api/cameras'
import { ElMessage, ElMessageBox } from 'element-plus'
import CameraPlayer from '@/components/CameraPlayer.vue'
import { useNotificationsStore } from '@/stores/notifications'

const recordings = ref([])
const total = ref(0)
const loading = ref(false)
const cameras = ref([])
const playDialog = ref(false)
const playUrl = ref('')
const notifications = useNotificationsStore()

const filter = ref({ camera_mac: '', date: '', page: 1, page_size: 20 })

onMounted(async () => {
  const { data } = await listCameras()
  cameras.value = data
  fetchRecordings()
})

watch(
  () => notifications.lastRecordingEvent,
  () => {
    fetchRecordings()
  },
)

async function fetchRecordings() {
  loading.value = true
  try {
    const params = { page: filter.value.page, page_size: filter.value.page_size }
    if (filter.value.camera_mac) params.camera_mac = filter.value.camera_mac
    if (filter.value.date) params.date = filter.value.date
    const { data } = await listRecordings(params)
    recordings.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function playRecording(rec) {
  const token = localStorage.getItem('token')
  playUrl.value = streamUrl(rec.id) + `?token=${token}`
  playDialog.value = true
}

async function handleDelete(rec) {
  try {
    await ElMessageBox.confirm('确定删除该录像？', '确认删除', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteRecording(rec.id)
    ElMessage.success('已删除')
    fetchRecordings()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '删除失败，请稍后重试')
  }
}

function downloadRecording(rec) {
  const token = localStorage.getItem('token')
  const url = downloadUrl(rec.id) + `?token=${token}`
  const a = document.createElement('a')
  a.href = url
  a.download = `recording_${rec.id}.mp4`
  a.click()
}

function formatSize(bytes) {
  if (!bytes) return '-'
  return bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
function formatDuration(s) {
  if (!s) return '-'
  const m = Math.floor(s / 60),
    sec = s % 60
  return `${m}:${String(sec).padStart(2, '0')}`
}
function statusType(s) {
  return { completed: 'success', recording: 'warning', failed: 'danger', synced: 'info' }[s] || ''
}
</script>

<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">录像库</h2>
    </div>

    <el-form :inline="true" :model="filter" class="filter-bar">
      <el-form-item label="摄像头">
        <el-select v-model="filter.camera_mac" placeholder="全部" clearable style="width: 200px">
          <el-option v-for="c in cameras" :key="c.device_mac" :label="c.onvif_host" :value="c.device_mac" />
        </el-select>
      </el-form-item>
      <el-form-item label="日期">
        <el-date-picker v-model="filter.date" type="date" value-format="YYYY-MM-DD" placeholder="全部日期" clearable />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="fetchRecordings">查询</el-button>
      </el-form-item>
    </el-form>

    <el-table v-loading="loading" :data="recordings" stripe border style="width: 100%">
      <el-table-column prop="camera_mac" label="摄像头 MAC" min-width="160" />
      <el-table-column label="开始时间" width="170">
        <template #default="{ row }">{{ new Date(row.started_at).toLocaleString('zh-CN') }}</template>
      </el-table-column>
      <el-table-column label="时长" width="90">
        <template #default="{ row }">{{ formatDuration(row.duration) }}</template>
      </el-table-column>
      <el-table-column label="大小" width="100">
        <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" align="center">
        <template #default="{ row }">
          <el-tooltip :content="row.status === 'recording' ? '录制中，暂不可播放' : row.status === 'failed' ? '录制失败，无可用文件' : ''" :disabled="row.status !== 'recording' && row.status !== 'failed'">
            <el-button size="small" type="primary" :disabled="row.status === 'recording' || row.status === 'failed'" @click="playRecording(row)">播放</el-button>
          </el-tooltip>
          <el-button size="small" :disabled="row.status === 'recording' || row.status === 'failed'" @click="downloadRecording(row)" style="margin-left: 6px">下载</el-button>
          <el-button size="small" type="danger" style="margin-left: 6px" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination v-model:current-page="filter.page" :page-size="filter.page_size" :total="total" layout="total, prev, pager, next" class="pagination-bar" @current-change="fetchRecordings" />

    <el-dialog v-model="playDialog" title="录像回放" width="720px" destroy-on-close>
      <CameraPlayer :src="playUrl" />
    </el-dialog>
  </div>
</template>

<style scoped>
.filter-bar {
  margin-bottom: 16px;
}
</style>
