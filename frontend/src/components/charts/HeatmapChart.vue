<!-- src/components/charts/HeatmapChart.vue -->
<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as d3 from 'd3'
import { DEVICE_TYPE_COLORS, DEVICE_TYPE_LABELS } from './chartColors'

const props = defineProps({
  // 7d/30d mode: [{ day: 0-6, hour: 0-23, count: N, devices: string[] }]
  // 24h mode:    [{ day: 0,   hour: 0-23, minuteBlock: 0-5, count: N, devices: string[] }]
  data:        { type: Array,  default: () => [] },
  range:       { type: String, default: '7d' },   // '24h' | '7d' | '30d'
  deviceTypes: { type: Array,  default: () => [] }, // active type filters; [] = all
  height:      { type: Number, default: 200 },
})

const emit = defineEmits(['range-change', 'type-filter-change', 'cell-click'])

const svgRef     = ref(null)
const tooltipRef = ref(null)
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

function renderChart() {
  if (!svgRef.value || !props.data.length) return

  const cell = 22, pad = 3
  const isDay   = props.range === '24h'
  const rowLabels = isDay
    ? ['00', '10', '20', '30', '40', '50']
    : DAYS_7
  const rowCount = rowLabels.length
  const ml = 44, mt = 30

  const svgW = ml + 24 * (cell + pad)
  const svgH = mt + rowCount * (cell + pad) + 10

  d3.select(svgRef.value).selectAll('*').remove()
  const svg = d3.select(svgRef.value)
    .append('svg').attr('width', svgW).attr('height', svgH)
    .style('overflow', 'visible')

  const maxVal = d3.max(props.data, (d) => d.count) || 1
  const colorScale = d3.scaleSequential()
    .domain([0, maxVal])
    .interpolator(d3.interpolateRgb('#1e1e28', '#5E5CE6'))

  // Row labels
  svg.selectAll('.rl').data(rowLabels).join('text')
    .attr('x', ml - 6)
    .attr('y', (_, i) => mt + i * (cell + pad) + cell / 2 + 4)
    .attr('text-anchor', 'end').attr('font-size', 10).attr('fill', '#888')
    .text((d) => d)

  // Hour labels every 3h
  svg.selectAll('.hl').data(d3.range(0, 24, 3)).join('text')
    .attr('x', (h) => ml + h * (cell + pad) + cell / 2)
    .attr('y', mt - 8)
    .attr('text-anchor', 'middle').attr('font-size', 10).attr('fill', '#888')
    .text((h) => `${h}`)

  const tooltip = d3.select(tooltipRef.value)

  props.data.forEach((d) => {
    const col = d.hour
    const row = isDay ? (d.minuteBlock ?? 0) : d.day
    const x   = ml + col * (cell + pad)
    const y   = mt + row * (cell + pad)

    svg.append('rect')
      .attr('x', x).attr('y', y)
      .attr('width', cell).attr('height', cell)
      .attr('rx', 3)
      .attr('fill', d.count === 0
        ? 'var(--color-surface-raised, #252528)'
        : colorScale(d.count))
      .attr('stroke', 'var(--color-border, #333)')
      .attr('stroke-width', 0.5)
      .style('cursor', 'pointer')
      .on('mousemove', (event) => {
        const timeLabel = isDay
          ? `${d.hour}:${String((d.minuteBlock ?? 0) * 10).padStart(2, '0')}`
          : `${DAYS_7[d.day]} ${d.hour}:00`
        const list    = (d.devices || []).slice(0, 5).join('<br>')
        const more    = (d.devices || []).length > 5
          ? `<br><span style="color:#888">+${d.devices.length - 5} 台…</span>` : ''
        tooltip
          .style('display', 'block')
          .style('left',  event.clientX + 14 + 'px')
          .style('top',   event.clientY - 40 + 'px')
          .html(`<strong>${timeLabel}</strong><br>${d.count} 台在线${list ? '<br>' + list + more : ''}`)
      })
      .on('mouseleave', () => tooltip.style('display', 'none'))
      .on('click', () => emit('cell-click', { day: d.day, hour: d.hour, devices: d.devices || [] }))
  })
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
    </div>

    <div ref="containerRef">
      <div class="hm-scroll" :style="{ height: height + 'px' }">
        <div ref="svgRef" />
      </div>

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
.hm-scroll { overflow-x: auto; overflow-y: hidden; }
</style>
