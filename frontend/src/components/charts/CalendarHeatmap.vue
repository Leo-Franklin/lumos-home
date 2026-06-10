<!-- src/components/charts/CalendarHeatmap.vue -->
<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import * as d3 from 'd3'
import { useI18n } from 'vue-i18n'

const { t, tm, rt } = useI18n()

const props = defineProps({
  data: { type: Array, default: () => [] }, // [{ date: 'YYYY-MM-DD', count: number, duration_seconds?: number }]
  color: { type: String, default: 'var(--color-primary)' },
  days: { type: Number, default: 90 },
  showStats: { type: Boolean, default: true },
})

const containerRef = ref(null)
const svgRef = ref(null)
const tooltipRef = ref(null)
let ro = null

const stats = computed(() => {
  if (!props.data.length) return null
  const active = props.data.filter((d) => d.count > 0)
  const total = props.data.reduce((sum, d) => sum + d.count, 0)
  const peak = [...props.data].sort((a, b) => b.count - a.count)[0]
  return {
    activeDays: active.length,
    totalRecordings: total,
    peakDate: peak?.date ?? null,
    peakCount: peak?.count ?? 0,
  }
})

function resolveColor(cssVar, fallback) {
  if (!cssVar.startsWith('var(')) return cssVar
  const name = cssVar.slice(4, -1).trim()
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

function buildDayGrid() {
  const end = new Date()
  end.setHours(0, 0, 0, 0)
  const start = new Date(end)
  start.setDate(start.getDate() - (props.days - 1))

  const gridStart = new Date(start)
  gridStart.setDate(gridStart.getDate() - gridStart.getDay())

  const allDays = []
  const cur = new Date(gridStart)
  while (cur <= end) {
    allDays.push(new Date(cur))
    cur.setDate(cur.getDate() + 1)
  }
  return { allDays, rangeStart: start, rangeEnd: end }
}

function renderChart() {
  if (!svgRef.value || !containerRef.value) return
  d3.select(svgRef.value).selectAll('*').remove()

  const { allDays, rangeStart, rangeEnd } = buildDayGrid()
  const byDate = new Map(props.data.map((d) => [d.date, d]))
  const inRangeData = props.data.filter((d) => {
    const dt = new Date(d.date)
    return dt >= rangeStart && dt <= rangeEnd
  })
  const maxCount = d3.max(inRangeData, (d) => d.count) || 1

  const containerW = containerRef.value.clientWidth || 640
  const ml = 34
  const mt = 26
  const pad = 3
  const legendH = 22
  const numWeeks = Math.ceil(allDays.length / 7)
  const availW = containerW - ml - 12
  const rawCell = Math.floor((availW - pad * (numWeeks - 1)) / numWeeks)
  const cell = Math.max(11, Math.min(20, rawCell))
  const gridH = 7 * (cell + pad) - pad
  const svgH = mt + gridH + legendH + 6
  const W = containerW

  const baseColor = resolveColor('var(--color-surface-overlay)', '#2A2A32')
  const accentColor = resolveColor(props.color, '#6366F1')
  const colorScale = (count) => {
    if (count === 0) return null
    const t = Math.pow(count / maxCount, 0.55)
    return d3.interpolateRgb(baseColor, accentColor)(t)
  }

  const svg = d3.select(svgRef.value).append('svg').attr('width', W).attr('height', svgH)
  const tooltip = d3.select(tooltipRef.value)

  const gradId = 'cal-legend-grad'
  const defs = svg.append('defs')
  const grad = defs.append('linearGradient').attr('id', gradId)
  d3.range(11).forEach((i) => {
    const t = Math.pow(i / 10, 0.55)
    grad
      .append('stop')
      .attr('offset', `${i * 10}%`)
      .attr('stop-color', d3.interpolateRgb(baseColor, accentColor)(t))
  })

  const weekdayLabels = [0, 1, 2, 3, 4, 5, 6].map((i) => rt(tm('charts.weekdayShort')[i]))
  weekdayLabels.forEach((label, i) => {
    svg
      .append('text')
      .attr('class', 'cal-weekday')
      .attr('x', ml - 8)
      .attr('y', mt + i * (cell + pad) + cell * 0.72)
      .attr('text-anchor', 'end')
      .attr('font-size', 11)
      .attr('font-weight', 500)
      .attr('fill', 'var(--color-text-secondary)')
      .text(label)
  })

  const monthsSeen = new Set()
  allDays.forEach((d, i) => {
    const wk = Math.floor(i / 7)
    const key = `${d.getFullYear()}-${d.getMonth()}`
    if (!monthsSeen.has(key) && d.getDate() <= 7) {
      monthsSeen.add(key)
      svg
        .append('text')
        .attr('class', 'cal-month')
        .attr('x', ml + wk * (cell + pad))
        .attr('y', mt - 8)
        .attr('font-size', 10)
        .attr('font-weight', 500)
        .attr('fill', 'var(--color-text-secondary)')
        .text(t('charts.calendar.monthsFormat', { m: d3.timeFormat('%m')(d) }))
    }
  })

  allDays.forEach((d, i) => {
    const wk = Math.floor(i / 7)
    const dow = d.getDay()
    const dateStr = d3.timeFormat('%Y-%m-%d')(d)
    const inRange = d >= rangeStart && d <= rangeEnd
    const entry = byDate.get(dateStr)
    const count = inRange ? (entry?.count ?? 0) : 0
    const fill = colorScale(count)
    const isActive = count > 0

    svg
      .append('rect')
      .attr('x', ml + wk * (cell + pad))
      .attr('y', mt + dow * (cell + pad))
      .attr('width', cell)
      .attr('height', cell)
      .attr('rx', 3)
      .attr('fill', isActive ? fill : inRange ? 'var(--color-surface-overlay)' : 'transparent')
      .attr('stroke', isActive ? 'var(--color-primary-border)' : 'var(--color-border-subtle)')
      .attr('stroke-width', isActive ? 1 : 0.5)
      .attr('opacity', inRange ? 1 : 0.25)
      .style('cursor', inRange ? 'pointer' : 'default')
      .on(
        'mousemove',
        inRange
          ? (event) => {
              const dur = entry?.duration_seconds
                ? t('charts.calendar.minutes', { count: Math.round(entry.duration_seconds / 60) })
                : ''
              tooltip
                .style('display', 'block')
                .style('left', event.clientX + 14 + 'px')
                .style('top', event.clientY - 40 + 'px')
                .html(
                  `<strong>${dateStr}</strong><br>${t('charts.calendar.recordings', { count })}${dur}`,
                )
            }
          : null,
      )
      .on('mouseleave', inRange ? () => tooltip.style('display', 'none') : null)
  })

  const legendY = mt + gridH + 10
  const legendW = Math.min(180, W - ml - 80)
  svg
    .append('rect')
    .attr('x', ml)
    .attr('y', legendY)
    .attr('width', legendW)
    .attr('height', 6)
    .attr('rx', 3)
    .attr('fill', `url(#${gradId})`)

  svg
    .append('text')
    .attr('x', ml)
    .attr('y', legendY + 16)
    .attr('font-size', 10)
    .attr('fill', 'var(--color-text-muted)')
    .text(t('charts.calendar.legendLess'))

  svg
    .append('text')
    .attr('x', ml + legendW)
    .attr('y', legendY + 16)
    .attr('text-anchor', 'end')
    .attr('font-size', 10)
    .attr('fill', 'var(--color-text-muted)')
    .text(t('charts.calendar.legendMore', { count: maxCount }))
}

watch(() => [props.data, props.color, props.days], renderChart, { deep: true })
onMounted(() => {
  ro = new ResizeObserver(renderChart)
  ro.observe(containerRef.value)
  renderChart()
})
onUnmounted(() => ro?.disconnect())
</script>

<template>
  <div class="cal-wrap">
    <div v-if="showStats && stats" class="cal-stats">
      <div class="cal-stat">
        <span class="cal-stat-val tabular-nums">{{ stats.activeDays }}</span>
        <span class="cal-stat-lbl">{{ t('charts.calendar.activeDays') }}</span>
      </div>
      <div class="cal-stat">
        <span class="cal-stat-val tabular-nums">{{ stats.totalRecordings }}</span>
        <span class="cal-stat-lbl">{{ t('charts.calendar.totalRecordings') }}</span>
      </div>
      <div v-if="stats.peakDate" class="cal-stat">
        <span class="cal-stat-val cal-stat-val--sm">{{ stats.peakDate }}</span>
        <span class="cal-stat-lbl">
          {{ t('charts.calendar.peakDay', { count: stats.peakCount }) }}
        </span>
      </div>
    </div>

    <div ref="containerRef" class="cal-container">
      <div ref="svgRef" />
      <div
        ref="tooltipRef"
        class="chart-tooltip"
        style="display: none; position: fixed; z-index: 9999; pointer-events: none"
      />
    </div>
  </div>
</template>

<style scoped>
.cal-wrap {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  width: 100%;
}

.cal-stats {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border-subtle);
}
.cal-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 88px;
}
.cal-stat-val {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.2;
}
.cal-stat-val--sm {
  font-size: 13px;
  font-weight: 600;
  font-family: var(--font-mono);
}
.cal-stat-lbl {
  font-size: 11px;
  color: var(--color-text-muted);
}

.cal-container {
  width: 100%;
  overflow-x: auto;
}
</style>
