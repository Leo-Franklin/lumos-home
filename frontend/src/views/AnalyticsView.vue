<!-- src/views/AnalyticsView.vue -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import BaseChart       from '@/components/charts/BaseChart.vue'
import HeatmapChart    from '@/components/charts/HeatmapChart.vue'
import LineChart       from '@/components/charts/LineChart.vue'
import BarChart        from '@/components/charts/BarChart.vue'
import DonutChart      from '@/components/charts/DonutChart.vue'
import CalendarHeatmap from '@/components/charts/CalendarHeatmap.vue'
import { DEVICE_TYPE_COLORS, DEVICE_TYPE_LABELS } from '@/components/charts/chartColors'
import {
  getOnlineTrend, getDeviceTypeStats, getResponseTime,
  getRecordingCalendar, getNewDevices, getDeviceStability, getTypeActivity,
} from '@/api/analytics'
import { getDeviceHeatmap } from '@/api/devices'

const { t } = useI18n()
const router = useRouter()

function navigateToDevice(mac) {
  router.push({ path: '/devices', query: { mac } })
}

// ── ① Heatmap ──────────────────────────────────────────
const hmData    = ref([])
const hmRange   = ref('7d')
const hmTypes   = ref([])
const hmLoading = ref(false)

async function fetchHeatmap() {
  hmLoading.value = true
  try {
    const params = { range: hmRange.value }
    if (hmTypes.value.length) params.device_type = hmTypes.value.join(',')
    const { data } = await getDeviceHeatmap(params)
    hmData.value = (data.cells ?? []).map((c) => ({ day: c.day, hour: c.hour, count: c.value, devices: [] }))
  } catch { ElMessage.error(t('analytics.heatmapFailed')) }
  finally { hmLoading.value = false }
}

// ── ③ Online trend ──────────────────────────────────────
const trendData    = ref([])
const trendRange   = ref('7d')
const trendLoading = ref(false)

async function fetchTrend() {
  trendLoading.value = true
  try {
    const { data } = await getOnlineTrend({ range: trendRange.value })
    trendData.value = (data.data || []).map((d) => ({ x: new Date(d.timestamp), y: d.count }))
  } catch { ElMessage.error(t('analytics.trendFailed')) }
  finally { trendLoading.value = false }
}

// ── ② Device type ───────────────────────────────────────
const typeData    = ref([])
const typeLoading = ref(false)

async function fetchTypeStats() {
  typeLoading.value = true
  try {
    const { data } = await getDeviceTypeStats()
    typeData.value = (data.data || []).map((d) => ({
      label: DEVICE_TYPE_LABELS[d.type] || d.type,
      value: d.count,
      color: DEVICE_TYPE_COLORS[d.type] || '#8B8B96',
    }))
  } catch { ElMessage.error(t('analytics.typeStatsFailed')) }
  finally { typeLoading.value = false }
}

// ── ④ Response time ─────────────────────────────────────
const rtData    = ref([])
const rtLoading = ref(false)

async function fetchResponseTime() {
  rtLoading.value = true
  try {
    const { data } = await getResponseTime()
    rtData.value = (data.data || [])
      .map((d) => ({
        label:      d.name || d.mac,
        value:      d.avg_ms,
        valueLabel: `${Math.round(d.avg_ms)}ms`,
      }))
      .sort((a, b) => b.value - a.value) // slowest first — most actionable
  } catch { ElMessage.error(t('analytics.responseTimeFailed')) }
  finally { rtLoading.value = false }
}

// ── ⑤ Recording calendar ────────────────────────────────
const calData    = ref([])
const calLoading = ref(false)

async function fetchCalendar() {
  calLoading.value = true
  try {
    const { data } = await getRecordingCalendar({ range: '90d' })
    calData.value = data.data || []
  } catch { ElMessage.error(t('analytics.calendarFailed')) }
  finally { calLoading.value = false }
}

// ── ⑥ New devices ───────────────────────────────────────
const newDevData    = ref([])
const newDevLoading = ref(false)

async function fetchNewDevices() {
  newDevLoading.value = true
  try {
    const { data } = await getNewDevices({ range: '90d', group_by: 'week' })
    const items = data.data || []
    const prev4Avg = items.length >= 5
      ? items.slice(-5, -1).reduce((s, d) => s + d.count, 0) / 4
      : Infinity
    newDevData.value = items.map((d) => ({
      label: d.period,
      value: d.count,
      color: d.count > prev4Avg * 2 ? '#F07D38' : '#5E5CE6',
    }))
  } catch { ElMessage.error(t('analytics.newDevicesFailed')) }
  finally { newDevLoading.value = false }
}

// ── ⑦ Stability ─────────────────────────────────────────
const stabilityData    = ref([])
const stabilityRange   = ref('7d')
const stabilityLoading = ref(false)

function stabilityColor(pct) {
  if (pct >= 90) return '#26C281'
  if (pct >= 70) return '#F2C94C'
  return '#F07D38'
}

async function fetchStability() {
  stabilityLoading.value = true
  try {
    const { data } = await getDeviceStability({ range: stabilityRange.value })
    stabilityData.value = (data.data || [])
      .map((d) => ({
        label:      d.name || d.mac,
        value:      d.uptime_pct,
        valueLabel: `${(d.uptime_pct ?? 0).toFixed(1)}%`,
        color:      stabilityColor(d.uptime_pct ?? 0),
      }))
      .sort((a, b) => a.value - b.value) // least stable first — most actionable
  } catch { ElMessage.error(t('analytics.stabilityFailed')) }
  finally { stabilityLoading.value = false }
}

// ── ⑧ Type activity ─────────────────────────────────────
const activityData    = ref([])
const activityLoading = ref(false)

const ACTIVITY_GROUPS = Object.entries(DEVICE_TYPE_COLORS).map(([key, color]) => ({
  key, color, label: DEVICE_TYPE_LABELS[key],
}))

const TYPE_KEYS = Object.keys(DEVICE_TYPE_COLORS)

async function fetchTypeActivity() {
  activityLoading.value = true
  try {
    const { data } = await getTypeActivity({ range: '7d' })
    const items = data.data || []

    // Normalize each device type to its own peak (0–100) so small-population types
    // (e.g. 16 phones vs 178 computers) are visible on the same axis.
    const peaks = {}
    TYPE_KEYS.forEach((k) => {
      peaks[k] = Math.max(...items.map((d) => d[k] ?? 0)) || 1
    })

    activityData.value = items.map((d) => ({
      label: String(d.hour),
      ...Object.fromEntries(
        TYPE_KEYS.map((k) => [k, +((d[k] ?? 0) / peaks[k] * 100).toFixed(1)])
      ),
    }))
  } catch { ElMessage.error(t('analytics.typeActivityFailed')) }
  finally { activityLoading.value = false }
}

// ── Dynamic chart titles ─────────────────────────────────
const rtTitle        = computed(() => rtData.value.length        ? t('analytics.responseTimeTitle', { count: rtData.value.length })        : t('analytics.responseTimeTitleEmpty'))
const stabilityTitle = computed(() => stabilityData.value.length ? t('analytics.stabilityTitle', { count: stabilityData.value.length }) : t('analytics.stabilityTitleEmpty'))

async function fetchAll() {
  await Promise.all([
    fetchHeatmap(), fetchTrend(), fetchTypeStats(), fetchResponseTime(),
    fetchCalendar(), fetchNewDevices(), fetchStability(), fetchTypeActivity(),
  ])
}

onMounted(fetchAll)
</script>

<template>
  <div>
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ $t('analytics.title') }}</h2>
        <span class="page-sub">{{ $t('analytics.subtitle') }}</span>
      </div>
      <el-button :icon="Refresh" @click="fetchAll">{{ $t('analytics.refreshAll') }}</el-button>
    </div>

    <!-- ① 热力图 全宽 -->
    <BaseChart
      :title="$t('analytics.heatmapTitle')"
      :loading="hmLoading"
      :empty="false"
      style="margin-bottom:16px"
    >
      <HeatmapChart
        :data="hmData"
        :range="hmRange"
        :device-types="hmTypes"
        :height="250"
        @range-change="(r) => { hmRange = r; fetchHeatmap() }"
        @type-filter-change="(t) => { hmTypes = t; fetchHeatmap() }"
      />
    </BaseChart>

    <!-- Row 2: ③ 趋势 + ⑤ 日历 -->
    <div class="row-2 mb">
      <BaseChart
        :title="$t('analytics.onlineTrendTitle')"
        :loading="trendLoading"
        :empty="!trendLoading && !trendData.length"
        :range="trendRange"
        :ranges="[{ label: $t('analytics.range7d'), value: '7d' }, { label: $t('analytics.range30d'), value: '30d' }]"
        @range-change="(r) => { trendRange = r; fetchTrend() }"
      >
        <LineChart :data="trendData" color="#5E5CE6" :height="160" />
      </BaseChart>

      <BaseChart
        :title="$t('analytics.recordingCalendar')"
        :loading="calLoading"
        :empty="!calLoading && !calData.length"
      >
        <CalendarHeatmap :data="calData" :height="130" />
      </BaseChart>
    </div>

    <!-- Row 3: ② 类型分布 + ⑥ 新设备 + ⑧ 类型对比 -->
    <div class="row-3 mb">
      <BaseChart :title="$t('analytics.deviceTypeDist')" :loading="typeLoading" :empty="!typeLoading && !typeData.length">
        <DonutChart :data="typeData" :size="160" />
      </BaseChart>

      <BaseChart :title="$t('analytics.newDevicesTrend')" :loading="newDevLoading" :empty="!newDevLoading && !newDevData.length">
        <BarChart :data="newDevData" mode="vertical" :height="180" />
      </BaseChart>

      <BaseChart :title="$t('analytics.typeActivity')" :loading="activityLoading" :empty="!activityLoading && !activityData.length">
        <BarChart :data="activityData" mode="grouped" :groups="ACTIVITY_GROUPS" :height="160" />
        <!-- Inline legend -->
        <div class="type-legend">
          <span v-for="g in ACTIVITY_GROUPS" :key="g.key" class="type-legend-item">
            <span class="type-legend-dot" :style="{ background: g.color }" />
            {{ g.label }}
          </span>
        </div>
      </BaseChart>
    </div>

    <!-- Row 4: ④ 时延 + ⑦ 稳定性 -->
    <div class="row-2">
      <BaseChart
        :title="rtTitle"
        :loading="rtLoading"
        :empty="!rtLoading && !rtData.length"
      >
        <BarChart
          :data="rtData"
          mode="horizontal"
          :height="220"
          :scroll-max-height="400"
          :color-fn="(v) => v < 50 ? '#26C281' : v < 200 ? '#F2C94C' : '#F07D38'"
          @bar-click="(d) => navigateToDevice(d.label)"
        />
      </BaseChart>

      <BaseChart
        :title="stabilityTitle"
        :loading="stabilityLoading"
        :empty="!stabilityLoading && !stabilityData.length"
        :range="stabilityRange"
        :ranges="[{ label: $t('analytics.range7d'), value: '7d' }, { label: $t('analytics.range30d'), value: '30d' }]"
        @range-change="(r) => { stabilityRange = r; fetchStability() }"
      >
        <BarChart
          :data="stabilityData"
          mode="horizontal"
          :height="220"
          :scroll-max-height="400"
          @bar-click="(d) => navigateToDevice(d.label)"
        />
      </BaseChart>
    </div>
  </div>
</template>

<style scoped>
.mb { margin-bottom: 16px; }
.row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.row-3 { display: grid; grid-template-columns: 1fr 1fr 2fr; gap: 16px; }

/* Inline legend for grouped bar chart */
.type-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--color-border);
}
.type-legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--color-text-secondary);
}
.type-legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  flex-shrink: 0;
}
</style>
