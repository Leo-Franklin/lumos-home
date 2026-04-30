<!-- src/components/charts/HeatmapChart.vue -->
<script setup>
import { ref, watch, computed, onMounted, onUnmounted } from 'vue'
import * as d3 from 'd3'
import { DEVICE_TYPE_COLORS, DEVICE_TYPE_LABELS } from './chartColors'

const props = defineProps({
  data:        { type: Array,  default: () => [] },
  range:       { type: String, default: '7d' },
  deviceTypes: { type: Array,  default: () => [] },
  height:      { type: Number, default: 200 },
})

const emit = defineEmits(['range-change', 'type-filter-change', 'cell-click'])

const svgRef       = ref(null)
const tooltipRef   = ref(null)
const containerRef = ref(null)
let ro = null

const RANGES = [
  { label: '今日',   value: '24h' },
  { label: '近7天',  value: '7d'  },
  { label: '近30天', value: '30d' },
]

const TYPE_OPTIONS = Object.entries(DEVICE_TYPE_LABELS).map(([value, label]) => ({
  value, label, color: DEVICE_TYPE_COLORS[value],
}))

const DAYS_7 = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

// Background shading bands by time of day
const TIME_BANDS = [
  { start: 0,  end: 6,  label: '深夜', bg: 'rgba(30,20,50,0.55)'   },
  { start: 6,  end: 12, label: '上午', bg: 'rgba(20,30,50,0.40)'   },
  { start: 12, end: 18, label: '下午', bg: 'rgba(20,25,40,0.35)'   },
  { start: 18, end: 24, label: '傍晚', bg: 'rgba(30,15,45,0.50)'   },
]

// Derived summary stats shown in the toolbar
const stats = computed(() => {
  const active = props.data.filter((d) => d.count > 0)
  if (!active.length) return null

  const hourTotals = {}
  const dayTotals  = {}
  let total = 0

  props.data.forEach((d) => {
    hourTotals[d.hour] = (hourTotals[d.hour] || 0) + d.count
    const dk = d.day ?? 0
    dayTotals[dk] = (dayTotals[dk] || 0) + d.count
    total += d.count
  })

  const peakHour = Object.entries(hourTotals).sort((a, b) => b[1] - a[1])[0]?.[0]
  const peakDay  = Object.entries(dayTotals).sort((a, b) => b[1] - a[1])[0]?.[0]
  const maxCount = d3.max(props.data, (d) => d.count) || 1

  return {
    total,
    maxCount,
    peakHour: peakHour != null ? `${peakHour}:00` : '--',
    peakDay:  peakDay  != null ? (DAYS_7[+peakDay] || '--') : '--',
  }
})

function renderChart() {
  if (!svgRef.value || !containerRef.value) return

  const containerW = containerRef.value.clientWidth || 800
  const isDay      = props.range === '24h'
  const rowLabels  = isDay ? ['00', '10', '20', '30', '40', '50'] : DAYS_7
  const rowCount   = rowLabels.length

  // Layout constants
  const ml      = 46   // left margin for row labels
  const mt      = 38   // top margin for hour labels + zone labels
  const pad     = 3    // gap between cells
  const legendH = 28   // height of color-scale legend at bottom

  // Compute a responsive cell size that fills the full container width
  const availW = containerW - ml - 8
  const rawCell = Math.floor((availW - pad * 23) / 24)
  const cell    = Math.max(18, Math.min(40, rawCell))

  const svgH = mt + rowCount * (cell + pad) + legendH + 10

  d3.select(svgRef.value).selectAll('*').remove()
  const svg = d3.select(svgRef.value)
    .append('svg')
    .attr('width', containerW)
    .attr('height', svgH)

  const cellMap = new Map(
    props.data.map((d) => [`${isDay ? (d.minuteBlock ?? 0) : d.day}-${d.hour}`, d])
  )

  const maxVal = d3.max(props.data, (d) => d.count) || 1

  // Power-scale color interpolation — amplifies sparse data so even count=1 is clearly visible
  const colorScale = (v) => {
    if (v === 0) return null
    const t = Math.pow(v / maxVal, 0.4)
    return d3.interpolateRgb('#2a1f5e', '#5E5CE6')(t)
  }

  // ── Defs: gradient for color legend ──────────────────
  const gradId = 'hm-legend-grad'
  const defs = svg.append('defs')
  const grad = defs.append('linearGradient').attr('id', gradId)
  d3.range(11).forEach((i) => {
    const t = Math.pow(i / 10, 0.4)
    grad.append('stop')
      .attr('offset', `${i * 10}%`)
      .attr('stop-color', d3.interpolateRgb('#2a1f5e', '#5E5CE6')(t))
  })

  // ── Time-band background zones ────────────────────────
  const bandG = svg.append('g')
  TIME_BANDS.forEach(({ start, end, bg }) => {
    const x = ml + start * (cell + pad)
    const w = (end - start) * (cell + pad) - pad
    const h = rowCount * (cell + pad) - pad
    bandG.append('rect')
      .attr('x', x).attr('y', mt - 2)
      .attr('width', w).attr('height', h + 4)
      .attr('rx', 4)
      .attr('fill', bg)
  })

  // ── Time-band zone labels ─────────────────────────────
  TIME_BANDS.forEach(({ start, end, label }) => {
    const mid = (start + end) / 2
    svg.append('text')
      .attr('x', ml + mid * (cell + pad))
      .attr('y', mt - 20)
      .attr('text-anchor', 'middle')
      .attr('font-size', 9)
      .attr('fill', '#4a4a5a')
      .attr('letter-spacing', '0.06em')
      .text(label)
  })

  // ── Hour tick labels every 3 h ────────────────────────
  d3.range(0, 24, 3).forEach((h) => {
    svg.append('text')
      .attr('x', ml + h * (cell + pad) + cell / 2)
      .attr('y', mt - 8)
      .attr('text-anchor', 'middle')
      .attr('font-size', 9)
      .attr('fill', '#555')
      .text(h)
  })

  // ── Row labels ────────────────────────────────────────
  rowLabels.forEach((label, i) => {
    svg.append('text')
      .attr('x', ml - 8)
      .attr('y', mt + i * (cell + pad) + cell / 2 + 4)
      .attr('text-anchor', 'end')
      .attr('font-size', 10)
      .attr('fill', '#666')
      .text(label)
  })

  const tooltip = d3.select(tooltipRef.value)

  // ── Grid cells ────────────────────────────────────────
  for (let row = 0; row < rowCount; row++) {
    for (let col = 0; col < 24; col++) {
      const d = cellMap.get(`${row}-${col}`) ?? {
        day: isDay ? 0 : row,
        hour: col,
        minuteBlock: isDay ? row : undefined,
        count: 0,
        devices: [],
      }
      const x        = ml + col * (cell + pad)
      const y        = mt + row * (cell + pad)
      const fill     = colorScale(d.count)
      const isActive = d.count > 0

      svg.append('rect')
        .attr('x', x).attr('y', y)
        .attr('width', cell).attr('height', cell)
        .attr('rx', 3)
        .attr('fill',         isActive ? fill : 'rgba(255,255,255,0.03)')
        .attr('stroke',       isActive ? 'rgba(94,92,230,0.35)' : 'rgba(255,255,255,0.05)')
        .attr('stroke-width', isActive ? 1 : 0.5)
        .style('cursor', isActive ? 'pointer' : 'default')
        .on('mousemove', isActive ? (event) => {
          const timeLabel = isDay
            ? `${d.hour}:${String((d.minuteBlock ?? 0) * 10).padStart(2, '0')}`
            : `${DAYS_7[d.day ?? row]} ${d.hour}:00`
          const list = (d.devices || []).slice(0, 5).join('<br>')
          const more = (d.devices || []).length > 5
            ? `<br><span style="color:#888">+${d.devices.length - 5} 台…</span>` : ''
          tooltip
            .style('display', 'block')
            .style('left', event.clientX + 14 + 'px')
            .style('top',  event.clientY - 40 + 'px')
            .html(`<strong>${timeLabel}</strong><br>${d.count} 台在线${list ? '<br>' + list + more : ''}`)
        } : null)
        .on('mouseleave', isActive ? () => tooltip.style('display', 'none') : null)
        .on('click', isActive
          ? () => emit('cell-click', { day: d.day ?? row, hour: d.hour, devices: d.devices || [] })
          : null)
    }
  }

  // ── Color-scale legend ────────────────────────────────
  const legendY = mt + rowCount * (cell + pad) + 10
  const legendW = Math.min(160, containerW - ml - 80)

  svg.append('rect')
    .attr('x', ml).attr('y', legendY)
    .attr('width', legendW).attr('height', 6)
    .attr('rx', 3)
    .attr('fill', `url(#${gradId})`)

  svg.append('text')
    .attr('x', ml).attr('y', legendY + 17)
    .attr('font-size', 9).attr('fill', '#444')
    .text('0')

  svg.append('text')
    .attr('x', ml + legendW).attr('y', legendY + 17)
    .attr('text-anchor', 'end')
    .attr('font-size', 9).attr('fill', '#666')
    .text(`${maxVal} 台`)
}

watch(() => [props.data, props.range], renderChart, { deep: true })
onMounted(() => {
  ro = new ResizeObserver(renderChart)
  ro.observe(containerRef.value)
  renderChart()
})
onUnmounted(() => ro?.disconnect())
</script>

<template>
  <div>
    <div class="hm-toolbar">
      <el-radio-group :model-value="range" size="small" @change="emit('range-change', $event)">
        <el-radio-button v-for="r in RANGES" :key="r.value" :value="r.value">
          {{ r.label }}
        </el-radio-button>
      </el-radio-group>

      <div class="hm-filters">
        <button
          v-for="t in TYPE_OPTIONS"
          :key="t.value"
          class="type-chip"
          :class="{ active: deviceTypes.includes(t.value) }"
          :style="deviceTypes.includes(t.value)
            ? { color: t.color, borderColor: t.color + '88', background: t.color + '18' }
            : {}"
          @click="emit('type-filter-change', deviceTypes.includes(t.value)
            ? deviceTypes.filter((v) => v !== t.value)
            : [...deviceTypes, t.value])"
        >
          {{ t.label }}
        </button>
      </div>

      <!-- Derived summary stats -->
      <div v-if="stats" class="hm-stats">
        <div class="hm-stat">
          <span class="hm-stat-val">{{ stats.peakHour }}</span>
          <span class="hm-stat-lbl">峰值时段</span>
        </div>
        <div v-if="range !== '24h'" class="hm-stat">
          <span class="hm-stat-val">{{ stats.peakDay }}</span>
          <span class="hm-stat-lbl">最活跃日</span>
        </div>
        <div class="hm-stat">
          <span class="hm-stat-val">{{ stats.total }}</span>
          <span class="hm-stat-lbl">总事件数</span>
        </div>
      </div>
    </div>

    <div ref="containerRef" class="hm-container">
      <div ref="svgRef" />
      <div
        ref="tooltipRef"
        class="chart-tooltip"
        style="display:none;position:fixed;z-index:9999;pointer-events:none"
      />
    </div>
  </div>
</template>

<style scoped>
.hm-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.hm-filters { display: flex; gap: 6px; flex-wrap: wrap; }
.type-chip {
  padding: 2px 10px;
  font-size: 11px;
  border: 1px solid var(--color-border);
  border-radius: 20px;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: all 0.15s;
}
.type-chip:hover { color: var(--color-text-primary); }

.hm-container { width: 100%; overflow-x: hidden; }

/* Summary stats pushed to the right end of the toolbar */
.hm-stats {
  display: flex;
  gap: 20px;
  margin-left: auto;
  padding-left: 8px;
}
.hm-stat {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 1px;
}
.hm-stat-val {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  line-height: 1.2;
}
.hm-stat-lbl {
  font-size: 9px;
  color: var(--color-text-muted);
  letter-spacing: 0.04em;
}
</style>
