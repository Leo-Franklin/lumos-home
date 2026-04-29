<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { getDashboard } from '@/api/system'
import { Refresh } from '@element-plus/icons-vue'

const data = ref(null)
const loading = ref(false)
const error = ref('')
let timer = null

async function fetchDashboard() {
  loading.value = true
  error.value = ''
  try {
    const { data: d } = await getDashboard()
    data.value = d
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function formatDuration(seconds) {
  if (!seconds) return '0 分钟'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return h > 0 ? `${h} 小时 ${m} 分钟` : `${m} 分钟`
}

onMounted(() => {
  fetchDashboard()
  timer = setInterval(fetchDashboard, 30000)
})

onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">仪表板</h2>
      <el-button :icon="Refresh" :loading="loading" @click="fetchDashboard">刷新</el-button>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon style="margin-bottom: 16px" />
    <el-skeleton v-if="!data && loading" :rows="4" animated />

    <template v-if="data">
      <div class="stats-grid">

        <div class="stat-card">
          <div class="stat-header">成员在家</div>
          <div class="stat-value">
            {{ data.members_home }}<span class="stat-of"> / {{ data.members_total }}</span>
          </div>
          <div class="stat-desc">名成员当前在家</div>
        </div>

        <div class="stat-card">
          <div class="stat-header">摄像头</div>
          <div class="stat-value">
            {{ data.cameras_online }}<span class="stat-of"> / {{ data.cameras_total }}</span>
          </div>
          <div class="stat-desc">
            台在线
            <span v-if="data.cameras_recording > 0" class="tag-recording">
              · {{ data.cameras_recording }} 台录制中
            </span>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-header">网络设备</div>
          <div class="stat-value">
            {{ data.devices_online }}<span class="stat-of"> / {{ data.devices_total }}</span>
          </div>
          <div class="stat-desc">台设备在线</div>
        </div>

        <div class="stat-card">
          <div class="stat-header">今日录像</div>
          <div class="stat-value">{{ data.recordings_today_count }}</div>
          <div class="stat-desc">条 · {{ formatDuration(data.recordings_today_duration_seconds) }}</div>
        </div>

        <div class="stat-card" :class="{ 'stat-card--warn': data.unknown_devices_today > 0 }">
          <div class="stat-header">陌生设备</div>
          <div class="stat-value">{{ data.unknown_devices_today }}</div>
          <div class="stat-desc">台今日首次出现</div>
        </div>

      </div>
    </template>
  </div>
</template>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.stat-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 20px 20px 16px;
}

.stat-card--warn {
  border-color: rgba(230, 162, 60, 0.5);
  background: rgba(230, 162, 60, 0.05);
}

.stat-header {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 12px;
}

.stat-value {
  font-size: 40px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1;
  margin-bottom: 8px;
}

.stat-of {
  font-size: 22px;
  font-weight: 400;
  color: var(--color-text-muted);
}

.stat-desc {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.tag-recording {
  color: var(--color-danger, #f05252);
  font-weight: 600;
}
</style>
