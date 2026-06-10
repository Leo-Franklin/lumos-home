<!-- src/views/AnalyticsView.vue -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { useRouter, useRoute } from 'vue-router'
import BaseChart from '@/components/charts/BaseChart.vue'
import HeatmapChart from '@/components/charts/HeatmapChart.vue'
import LineChart from '@/components/charts/LineChart.vue'
import CalendarHeatmap from '@/components/charts/CalendarHeatmap.vue'
import RingGauge from '@/components/charts/RingGauge.vue'
import ActivityInsightPanel from '@/components/analytics/ActivityInsightPanel.vue'
import NetworkOverviewPanel from '@/components/analytics/NetworkOverviewPanel.vue'
import DeviceHealthTable from '@/components/analytics/DeviceHealthTable.vue'
import { DEVICE_TYPE_COLORS, DEVICE_TYPE_LABELS } from '@/components/charts/chartColors'
import {
  getOnlineTrend,
  getDeviceTypeStats,
  getResponseTime,
  getRecordingCalendar,
  getDeviceStability,
} from '@/api/analytics'
import { getDeviceHeatmap } from '@/api/devices'
import { getDashboard } from '@/api/system'
import { useApiError } from '@/composables/useApiError'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const handleError = useApiError()

const refreshing = ref(false)
const dashboard = ref(null)
const dashboardLoading = ref(false)

async function navigateToDevice(mac) {
  if (!mac) return
  if (route.path !== '/devices') {
    await router.push('/devices')
  }
  await router.push({ path: '/devices', query: { mac } })
}

// ── Dashboard snapshot ────────────────────────────────────
async function fetchDashboard() {
  dashboardLoading.value = true
  try {
    const { data } = await getDashboard()
    dashboard.value = data
  } catch (e) {
    handleError(e, 'dashboard.loadFailed')
  } finally {
    dashboardLoading.value = false
  }
}

// ── Heatmap ─────────────────────────────────────────────
const hmData = ref([])
const hmRange = ref('7d')
const hmTypes = ref([])
const hmLoading = ref(false)

async function fetchHeatmap() {
  hmLoading.value = true
  try {
    const params = { range: hmRange.value }
    if (hmTypes.value.length) params.device_type = hmTypes.value.join(',')
    const { data } = await getDeviceHeatmap(params)
    hmData.value = (data.cells ?? []).map((c) => ({
      day: c.day,
      hour: c.hour,
      count: c.value,
      devices: [],
    }))
  } catch (e) {
    handleError(e, 'analytics.heatmapFailed')
  } finally {
    hmLoading.value = false
  }
}

// ── Online trend ──────────────────────────────────────────
const trendData = ref([])
const trendRange = ref('7d')
const trendLoading = ref(false)

async function fetchTrend() {
  trendLoading.value = true
  try {
    const { data } = await getOnlineTrend({ range: trendRange.value })
    trendData.value = (data.data || []).map((d) => ({ x: new Date(d.timestamp), y: d.count }))
  } catch (e) {
    handleError(e, 'analytics.trendFailed')
  } finally {
    trendLoading.value = false
  }
}

// ── Device type ───────────────────────────────────────────
const typeData = ref([])
const typeLoading = ref(false)

async function fetchTypeStats() {
  typeLoading.value = true
  try {
    const { data } = await getDeviceTypeStats()
    typeData.value = (data.data || []).map((d) => ({
      label: DEVICE_TYPE_LABELS[d.type] || d.type,
      value: d.count,
      color: DEVICE_TYPE_COLORS[d.type] || 'var(--color-type-unknown)',
    }))
  } catch (e) {
    handleError(e, 'analytics.typeStatsFailed')
  } finally {
    typeLoading.value = false
  }
}

// ── Response time ─────────────────────────────────────────
const rtData = ref([])
const rtLoading = ref(false)

async function fetchResponseTime() {
  rtLoading.value = true
  try {
    const { data } = await getResponseTime()
    rtData.value = (data.data || []).map((d) => ({
      label: d.name || d.mac,
      mac: d.mac,
      value: d.avg_ms,
    }))
  } catch (e) {
    handleError(e, 'analytics.responseTimeFailed')
  } finally {
    rtLoading.value = false
  }
}

// ── Recording calendar ────────────────────────────────────
const calData = ref([])
const calLoading = ref(false)

async function fetchCalendar() {
  calLoading.value = true
  try {
    const { data } = await getRecordingCalendar({ range: '90d' })
    calData.value = data.data || []
  } catch (e) {
    handleError(e, 'analytics.calendarFailed')
  } finally {
    calLoading.value = false
  }
}

// ── Stability ─────────────────────────────────────────────
const stabilityData = ref([])
const stabilityRange = ref('7d')
const stabilityLoading = ref(false)

async function fetchStability() {
  stabilityLoading.value = true
  try {
    const { data } = await getDeviceStability({ range: stabilityRange.value })
    stabilityData.value = (data.data || []).map((d) => ({
      label: d.name || d.mac,
      mac: d.mac,
      value: d.uptime_pct,
    }))
  } catch (e) {
    handleError(e, 'analytics.stabilityFailed')
  } finally {
    stabilityLoading.value = false
  }
}

// ── Health helpers ────────────────────────────────────────
function healthStatus(latency, uptime) {
  const latBad = latency != null && latency >= 200
  const latWarn = latency != null && latency >= 50
  const upBad = uptime != null && uptime < 70
  const upWarn = uptime != null && uptime < 90
  if (latBad || upBad) return 'critical'
  if (latWarn || upWarn) return 'warning'
  return 'good'
}

function deviceSeverity(latency, uptime) {
  let score = 0
  if (latency != null) score += latency >= 200 ? 100 : latency >= 50 ? 40 : 0
  if (uptime != null) score += uptime < 70 ? 100 : uptime < 90 ? 40 : 0
  return score
}

function deviceHealthScore(latency, uptime) {
  let score = 100
  if (latency != null) {
    if (latency >= 200) score -= 40
    else if (latency >= 50) score -= 15
  }
  if (uptime != null) {
    if (uptime < 70) score -= 40
    else if (uptime < 90) score -= 15
  }
  return Math.max(0, score)
}

const mergedHealth = computed(() => {
  const map = new Map()
  rtData.value.forEach((d) => {
    map.set(d.mac, { label: d.label, mac: d.mac, latency: d.value, uptime: null })
  })
  stabilityData.value.forEach((d) => {
    const row = map.get(d.mac) || { label: d.label, mac: d.mac, latency: null, uptime: null }
    map.set(d.mac, { ...row, label: d.label || row.label, uptime: d.value })
  })
  return [...map.values()]
    .map((row) => ({
      ...row,
      status: healthStatus(row.latency, row.uptime),
      severity: deviceSeverity(row.latency, row.uptime),
      score: deviceHealthScore(row.latency, row.uptime),
    }))
    .sort((a, b) => b.severity - a.severity || a.score - b.score)
})

const healthIssues = computed(() =>
  mergedHealth.value.filter((r) => r.status !== 'good').slice(0, 12),
)

const networkHealth = computed(() => {
  if (!mergedHealth.value.length) return null
  const avg = mergedHealth.value.reduce((sum, r) => sum + r.score, 0) / mergedHealth.value.length
  return Math.round(avg)
})

const avgLatency = computed(() => {
  if (!rtData.value.length) return null
  const sum = rtData.value.reduce((s, d) => s + d.value, 0)
  return Math.round(sum / rtData.value.length)
})

const avgUptime = computed(() => {
  if (!stabilityData.value.length) return null
  const sum = stabilityData.value.reduce((s, d) => s + d.value, 0)
  return +(sum / stabilityData.value.length).toFixed(1)
})

// ── Activity insights ─────────────────────────────────────
const peakHour = computed(() => {
  const active = hmData.value.filter((d) => d.count > 0)
  if (!active.length) return null
  const hourTotals = {}
  active.forEach((d) => {
    hourTotals[d.hour] = (hourTotals[d.hour] || 0) + d.count
  })
  const peak = Object.entries(hourTotals).sort((a, b) => b[1] - a[1])[0]?.[0]
  return peak != null ? `${peak}:00` : null
})

const avgDailyOnline = computed(() => {
  if (!trendData.value.length) return null
  const sum = trendData.value.reduce((s, d) => s + d.y, 0)
  return Math.round(sum / trendData.value.length)
})

const trendDelta = computed(() => {
  if (trendData.value.length < 2) return null
  const first = trendData.value[0].y
  const last = trendData.value[trendData.value.length - 1].y
  return last - first
})

const recordingActiveDays = computed(() => {
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - 30)
  return calData.value.filter((d) => new Date(d.date) >= cutoff && d.count > 0).length
})

const insightItems = computed(() => [
  {
    key: 'peak',
    label: t('analytics.insightPeakHour'),
    value: peakHour.value ?? t('analytics.kpiEmpty'),
    hint: t('analytics.insightPeakHourHint'),
    accent: 'var(--color-primary)',
  },
  {
    key: 'avg',
    label: t('analytics.insightAvgOnline'),
    value: avgDailyOnline.value ?? t('analytics.kpiEmpty'),
    hint: t('analytics.insightAvgOnlineHint'),
    accent: 'var(--color-accent-devices)',
  },
  {
    key: 'delta',
    label: t('analytics.insightTrendDelta'),
    value:
      trendDelta.value == null
        ? t('analytics.kpiEmpty')
        : `${trendDelta.value > 0 ? '+' : ''}${trendDelta.value}`,
    hint: t('analytics.insightTrendDeltaHint'),
    accent: trendDelta.value > 0 ? 'var(--color-online)' : 'var(--color-text-muted)',
    warn: trendDelta.value != null && trendDelta.value < 0,
  },
  {
    key: 'recording',
    label: t('analytics.insightRecordingDays'),
    value: recordingActiveDays.value ?? t('analytics.kpiEmpty'),
    hint: t('analytics.insightRecordingDaysHint'),
    accent: 'var(--color-accent-recordings)',
  },
])

const insightLoading = computed(() => hmLoading.value || trendLoading.value || calLoading.value)

// ── KPI cards ─────────────────────────────────────────────
const kpiCards = computed(() => {
  const d = dashboard.value
  return [
    {
      key: 'devices',
      label: t('analytics.kpiDevices'),
      value: d ? `${d.devices_online}` : null,
      suffix: d ? `/ ${d.devices_total}` : '',
      desc: t('analytics.kpiDevicesDesc'),
      accent: 'var(--color-accent-devices)',
      warn: false,
    },
    {
      key: 'cameras',
      label: t('analytics.kpiCameras'),
      value: d ? `${d.cameras_online}` : null,
      suffix: d ? `/ ${d.cameras_total}` : '',
      desc:
        d && d.cameras_recording > 0
          ? t('analytics.kpiCamerasRecording', { count: d.cameras_recording })
          : t('analytics.kpiCamerasDesc'),
      accent: 'var(--color-accent-cameras)',
      warn: false,
    },
    {
      key: 'recordings',
      label: t('analytics.kpiRecordings'),
      value: d?.recordings_today_count ?? null,
      suffix: '',
      desc: t('analytics.kpiRecordingsDesc'),
      accent: 'var(--color-accent-recordings)',
      warn: false,
    },
    {
      key: 'health',
      label: t('analytics.kpiHealth'),
      value: networkHealth.value != null ? `${networkHealth.value}%` : null,
      suffix: '',
      desc: t('analytics.kpiHealthDesc'),
      accent: 'var(--color-primary)',
      warn: networkHealth.value != null && networkHealth.value < 70,
    },
    {
      key: 'issues',
      label: t('analytics.kpiIssues'),
      value: healthIssues.value.length,
      suffix: '',
      desc: t('analytics.kpiIssuesDesc'),
      accent: 'var(--color-warning)',
      warn: healthIssues.value.length > 0,
    },
  ]
})

const perfLoading = computed(() => rtLoading.value || stabilityLoading.value)

async function fetchAll() {
  refreshing.value = true
  try {
    await Promise.all([
      fetchDashboard(),
      fetchHeatmap(),
      fetchTrend(),
      fetchTypeStats(),
      fetchResponseTime(),
      fetchCalendar(),
      fetchStability(),
    ])
  } finally {
    refreshing.value = false
  }
}

onMounted(fetchAll)
</script>

<template>
  <div class="analytics-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ $t('analytics.title') }}</h2>
        <span class="page-sub">{{ $t('analytics.subtitle') }}</span>
      </div>
      <div class="header-actions">
        <el-button :icon="Refresh" :loading="refreshing" @click="fetchAll">
          {{ $t('analytics.refreshAll') }}
        </el-button>
      </div>
    </div>

    <div class="kpi-grid">
      <div
        v-for="card in kpiCards"
        :key="card.key"
        class="kpi-card glass-card"
        :class="{ 'kpi-card--warn': card.warn }"
      >
        <div class="kpi-accent" :style="{ background: card.accent }" />
        <div class="kpi-label">{{ card.label }}</div>
        <div class="kpi-value tabular-nums">
          {{ card.value ?? $t('analytics.kpiEmpty')
          }}<span v-if="card.suffix" class="kpi-suffix">{{ card.suffix }}</span>
        </div>
        <div class="kpi-desc">{{ card.desc }}</div>
      </div>
    </div>

    <!-- 活跃与趋势 -->
    <section class="analytics-section">
      <div class="section-intro">
        <h3 class="section-title">{{ $t('analytics.sectionActivity') }}</h3>
        <p class="section-desc">{{ $t('analytics.sectionActivityDesc') }}</p>
      </div>

      <BaseChart
        :title="$t('analytics.heatmapTitle')"
        :subtitle="$t('analytics.heatmapSubtitle')"
        :loading="hmLoading"
        :empty="false"
        featured
      >
        <HeatmapChart
          :data="hmData"
          :range="hmRange"
          :device-types="hmTypes"
          :height="260"
          @range-change="
            (r) => {
              hmRange = r
              fetchHeatmap()
            }
          "
          @type-filter-change="
            (types) => {
              hmTypes = types
              fetchHeatmap()
            }
          "
        />
      </BaseChart>

      <div class="activity-row">
        <BaseChart
          class="activity-trend"
          :title="$t('analytics.onlineTrendTitle')"
          :subtitle="$t('analytics.onlineTrendSubtitle')"
          :loading="trendLoading"
          :empty="!trendLoading && !trendData.length"
          :range="trendRange"
          :ranges="[
            { label: $t('analytics.range7d'), value: '7d' },
            { label: $t('analytics.range30d'), value: '30d' },
          ]"
          @range-change="
            (r) => {
              trendRange = r
              fetchTrend()
            }
          "
        >
          <LineChart :data="trendData" color="var(--color-primary)" :height="200" />
        </BaseChart>

        <BaseChart
          :title="$t('analytics.insightsTitle')"
          :subtitle="$t('analytics.insightsSubtitle')"
          :loading="insightLoading"
          :empty="false"
        >
          <ActivityInsightPanel :items="insightItems" />
        </BaseChart>
      </div>

      <BaseChart
        :title="$t('analytics.recordingCalendar')"
        :subtitle="$t('analytics.recordingCalendarSubtitle')"
        :loading="calLoading"
        :empty="!calLoading && !calData.length"
      >
        <CalendarHeatmap :data="calData" :days="90" />
      </BaseChart>
    </section>

    <!-- 网络概览 -->
    <section class="analytics-section">
      <div class="section-intro">
        <h3 class="section-title">{{ $t('analytics.sectionOverview') }}</h3>
        <p class="section-desc">{{ $t('analytics.sectionOverviewDesc') }}</p>
      </div>

      <BaseChart
        :title="$t('analytics.overviewTitle')"
        :subtitle="$t('analytics.overviewSubtitle')"
        :loading="typeLoading || dashboardLoading"
        :empty="!typeLoading && !dashboardLoading && !typeData.length && !dashboard"
      >
        <NetworkOverviewPanel
          :type-data="typeData"
          :online="dashboard?.devices_online ?? 0"
          :total="dashboard?.devices_total ?? 0"
          :unknown-today="dashboard?.unknown_devices_today ?? 0"
        />
      </BaseChart>
    </section>

    <!-- 性能诊断 -->
    <section class="analytics-section">
      <div class="section-intro">
        <h3 class="section-title">{{ $t('analytics.sectionPerformance') }}</h3>
        <p class="section-desc">{{ $t('analytics.sectionPerformanceDesc') }}</p>
      </div>

      <div class="perf-row">
        <div class="perf-summary glass-card">
          <el-skeleton v-if="perfLoading" :rows="4" animated />
          <template v-else>
            <RingGauge
              :value="networkHealth ?? 0"
              :size="128"
              :label="$t('analytics.healthScoreLabel')"
            />
            <div class="perf-stats">
              <div class="perf-stat">
                <span class="perf-stat-label">{{ $t('analytics.avgLatency') }}</span>
                <span class="perf-stat-value tabular-nums">
                  {{ avgLatency != null ? `${avgLatency}ms` : '—' }}
                </span>
              </div>
              <div class="perf-stat">
                <span class="perf-stat-label">{{ $t('analytics.avgUptime') }}</span>
                <span class="perf-stat-value tabular-nums">
                  {{ avgUptime != null ? `${avgUptime}%` : '—' }}
                </span>
              </div>
              <div class="perf-stat" :class="{ 'perf-stat--warn': healthIssues.length > 0 }">
                <span class="perf-stat-label">{{ $t('analytics.issueDevices') }}</span>
                <span class="perf-stat-value tabular-nums">{{ healthIssues.length }}</span>
              </div>
            </div>
          </template>
        </div>

        <BaseChart
          class="perf-table-card"
          :title="$t('analytics.healthTableTitle')"
          :subtitle="$t('analytics.healthTableSubtitle')"
          :loading="perfLoading"
          :empty="false"
          :range="stabilityRange"
          :ranges="[
            { label: $t('analytics.range7d'), value: '7d' },
            { label: $t('analytics.range30d'), value: '30d' },
          ]"
          @range-change="
            (r) => {
              stabilityRange = r
              fetchStability()
            }
          "
        >
          <DeviceHealthTable
            v-if="healthIssues.length"
            :rows="healthIssues"
            @row-click="(row) => navigateToDevice(row.mac)"
          />
          <div v-else class="health-all-good">{{ $t('analytics.healthAllGood') }}</div>
          <template v-if="healthIssues.length" #footer>
            <p class="chart-hint">{{ $t('analytics.barClickHint') }}</p>
          </template>
        </BaseChart>
      </div>
    </section>
  </div>
</template>

<style scoped>
.analytics-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--space-4);
}

.kpi-card {
  position: relative;
  overflow: hidden;
  padding: var(--space-4) var(--space-5);
  min-height: 96px;
}
.kpi-card--warn {
  border-color: color-mix(in srgb, var(--color-warning) 35%, transparent);
  background: color-mix(in srgb, var(--color-warning) 6%, rgba(24, 24, 28, 0.8));
}
.kpi-accent {
  position: absolute;
  top: 0;
  left: 0;
  width: 3px;
  height: 100%;
  border-radius: var(--radius-full);
  opacity: 0.85;
}
.kpi-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  letter-spacing: 0.04em;
  margin-bottom: var(--space-2);
}
.kpi-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.1;
  margin-bottom: var(--space-1);
}
.kpi-suffix {
  font-size: 16px;
  font-weight: 400;
  color: var(--color-text-muted);
  margin-left: 2px;
}
.kpi-desc {
  font-size: 11px;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.analytics-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.section-intro {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.section-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
}
.section-desc {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.activity-row {
  display: grid;
  grid-template-columns: 1.75fr 1fr;
  gap: var(--space-4);
  align-items: stretch;
}

.perf-row {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: var(--space-4);
  align-items: stretch;
}

.perf-summary {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-5);
  padding: var(--space-5);
  min-height: 280px;
}
.perf-stats {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  width: 100%;
}
.perf-stat {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border-subtle);
}
.perf-stat--warn {
  border-color: color-mix(in srgb, var(--color-warning) 35%, transparent);
}
.perf-stat-label {
  font-size: 11px;
  color: var(--color-text-muted);
}
.perf-stat-value {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.chart-hint {
  margin: 0;
  font-size: 11px;
  color: var(--color-text-muted);
  line-height: 1.4;
}
.health-all-good {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: var(--color-online);
  font-size: 14px;
  font-weight: 500;
}

@media (max-width: 1200px) {
  .kpi-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .activity-row,
  .perf-row {
    grid-template-columns: 1fr;
  }
  .perf-summary {
    min-height: auto;
  }
}

@media (max-width: 767.98px) {
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
