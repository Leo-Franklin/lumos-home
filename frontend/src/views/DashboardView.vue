<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { getDashboard } from '@/api/system'
import { Refresh } from '@element-plus/icons-vue'
import LineChart  from '@/components/charts/LineChart.vue'
import BarChart   from '@/components/charts/BarChart.vue'
import DonutChart from '@/components/charts/DonutChart.vue'
import { DEVICE_TYPE_COLORS, DEVICE_TYPE_LABELS } from '@/components/charts/chartColors'
import { getOnlineTrend, getDeviceTypeStats, getNewDevices } from '@/api/analytics'
import { useFormatDuration } from '@/composables/useFormatDuration'

const { t } = useI18n()
const { formatDuration } = useFormatDuration()

const data = ref(null)
const loading = ref(false)
const error = ref('')
const sparkData   = ref([])
const donutData   = ref([])
const weekBarData = ref([])

async function fetchMiniCharts() {
  try {
    const [trend, types, newDev] = await Promise.all([
      getOnlineTrend({ range: '7d' }),
      getDeviceTypeStats(),
      getNewDevices({ range: '90d', group_by: 'week' }),
    ])
    sparkData.value = (trend.data.data || [])
      .map((d) => ({ x: new Date(d.timestamp), y: d.count }))
    donutData.value = (types.data.data || []).map((d) => ({
      label: DEVICE_TYPE_LABELS[d.type] || d.type,
      value: d.count,
      color: DEVICE_TYPE_COLORS[d.type] || '#8B8B96',
    }))
    weekBarData.value = (newDev.data.data || []).slice(-7).map((d) => ({
      label: d.period.slice(-2),
      value: d.count,
    }))
  } catch { /* mini charts are non-critical */ }
}
let timer = null

async function fetchDashboard() {
  loading.value = true
  error.value = ''
  try {
    const { data: d } = await getDashboard()
    data.value = d
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || t('dashboard.loadFailed')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchDashboard()
  fetchMiniCharts()
  timer = setInterval(fetchDashboard, 30000)
})

onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">{{ $t('dashboard.title') }}</h2>
      <el-button :icon="Refresh" :loading="loading" @click="fetchDashboard">{{ $t('common.refresh') }}</el-button>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon style="margin-bottom: 16px" />
    <el-skeleton v-if="!data && loading" :rows="4" animated />

    <template v-if="data">
      <div class="stats-grid">

        <div class="stat-card">
          <div class="stat-header">{{ $t('dashboard.membersHome') }}</div>
          <div class="stat-value">
            {{ data.members_home }}<span class="stat-of"> / {{ data.members_total }}</span>
          </div>
          <div class="stat-desc">{{ $t('dashboard.membersHomeDesc') }}</div>
        </div>

        <div class="stat-card">
          <div class="stat-header">{{ $t('dashboard.cameras') }}</div>
          <div class="stat-value">
            {{ data.cameras_online }}<span class="stat-of"> / {{ data.cameras_total }}</span>
          </div>
          <div class="stat-desc">
            {{ $t('dashboard.camerasOnline') }}
            <span v-if="data.cameras_recording > 0" class="tag-recording">
              · {{ data.cameras_recording }}{{ $t('dashboard.camerasRecording') }}
            </span>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-header">{{ $t('dashboard.networkDevices') }}</div>
          <div class="stat-value">
            {{ data.devices_online }}<span class="stat-of"> / {{ data.devices_total }}</span>
          </div>
          <div class="stat-desc">{{ $t('dashboard.devicesOnline') }}</div>
        </div>

        <div class="stat-card">
          <div class="stat-header">{{ $t('dashboard.todayRecordings') }}</div>
          <div class="stat-value">{{ data.recordings_today_count }}</div>
          <div class="stat-desc">{{ $t('common.unit_record') }} · {{ formatDuration(data.recordings_today_duration_seconds) }}</div>
        </div>

        <div class="stat-card" :class="{ 'stat-card--warn': data.unknown_devices_today > 0 }">
          <div class="stat-header">{{ $t('dashboard.unknownDevices') }}</div>
          <div class="stat-value">{{ data.unknown_devices_today }}</div>
          <div class="stat-desc">{{ $t('dashboard.todayAppeared') }}</div>
        </div>

      </div>

      <div v-if="sparkData.length || donutData.length" class="mini-charts">
        <div class="mini-card">
          <div class="mini-label">{{ $t('dashboard.onlineTrend') }}</div>
          <LineChart :data="sparkData" color="#5E5CE6" :height="60" :mini="true" />
        </div>
        <div class="mini-card">
          <div class="mini-label">{{ $t('dashboard.deviceTypes') }}</div>
          <DonutChart :data="donutData" :size="80" :mini="true" />
        </div>
        <div class="mini-card">
          <div class="mini-label">{{ $t('dashboard.newDevices') }}</div>
          <BarChart :data="weekBarData" mode="vertical" :height="60" :mini="true" />
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

.mini-charts {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-top: 16px;
}
.mini-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 14px 16px;
}
.mini-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 10px;
}
</style>
