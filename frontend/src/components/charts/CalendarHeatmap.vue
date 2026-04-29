<!-- src/components/charts/CalendarHeatmap.vue -->
<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  data:   { type: Array,  default: () => [] }, // [{ date: 'YYYY-MM-DD', count: number, duration_seconds: number }]
  color:  { type: String, default: '#5E5CE6' },
  height: { type: Number, default: 120 },
})

const containerRef = ref(null)
const svgRef       = ref(null)
const tooltipRef   = ref(null)
let ro = null

function renderChart() {
  if (!svgRef.value || !containerRef.value || !props.data.length) return
  d3.select(svgRef.value).selectAll('*').remove()

  const cell = 13, gap = 2, ml = 22, mt = 20
  const tooltip  = d3.select(tooltipRef.value)
  const byDate   = new Map(props.data.map((d) => [d.date, d]))
  const dates    = props.data.map((d) => new Date(d.date)).sort((a, b) => a - b)
  const firstDate = dates[0]
  const lastDate  = dates[dates.length - 1]

  // Align start to Sunday of first date's week
  const startDate = new Date(firstDate)
  startDate.setDate(startDate.getDate() - startDate.getDay())

  const allDays = []
  const cur = new Date(startDate)
  while (cur <= lastDate) { allDays.push(new Date(cur)); cur.setDate(cur.getDate() + 1) }

  const numWeeks = Math.ceil(allDays.length / 7)
  const W = Math.max(containerRef.value.clientWidth || 0, ml + numWeeks * (cell + gap))

  const maxCount  = d3.max(props.data, (d) => d.count) || 1
  const colorScale = d3.scaleSequential()
    .domain([0, maxCount])
    .interpolator(d3.interpolateRgb('#1e1e28', props.color))

  const svg = d3.select(svgRef.value)
    .append('svg').attr('width', W).attr('height', props.height)

  // Weekday labels (Sun, Tue, Thu, Sat)
  svg.selectAll('.dl')
    .data(['日', '二', '四', '六']).join('text')
    .attr('x', ml - 4)
    .attr('y', (_, i) => mt + [0, 2, 4, 6][i] * (cell + gap) + cell)
    .attr('text-anchor', 'end').attr('font-size', 9).attr('fill', '#666')
    .text((d) => d)

  // Month labels (first Sunday of each new month)
  const monthsSeen = new Set()
  allDays.forEach((d, i) => {
    const wk  = Math.floor(i / 7)
    const key = `${d.getFullYear()}-${d.getMonth()}`
    if (!monthsSeen.has(key) && d.getDay() === 0) {
      monthsSeen.add(key)
      svg.append('text')
        .attr('x', ml + wk * (cell + gap))
        .attr('y', mt - 4)
        .attr('font-size', 9).attr('fill', '#666')
        .text(d3.timeFormat('%m月')(d))
    }
  })

  // Cells
  allDays.forEach((d, i) => {
    const wk      = Math.floor(i / 7)
    const dow     = d.getDay()
    const dateStr = d3.timeFormat('%Y-%m-%d')(d)
    const entry   = byDate.get(dateStr)
    const count   = entry?.count ?? 0

    svg.append('rect')
      .attr('x', ml + wk * (cell + gap))
      .attr('y', mt + dow * (cell + gap))
      .attr('width', cell).attr('height', cell).attr('rx', 2)
      .attr('fill', count === 0 ? '#1e1e28' : colorScale(count))
      .style('cursor', 'pointer')
      .on('mousemove', (event) => {
        const dur = entry?.duration_seconds
          ? ` · ${Math.round(entry.duration_seconds / 60)} 分钟` : ''
        tooltip.style('display', 'block')
          .style('left', event.clientX + 14 + 'px')
          .style('top',  event.clientY - 40 + 'px')
          .html(`<strong>${dateStr}</strong><br>${count} 条录像${dur}`)
      })
      .on('mouseleave', () => tooltip.style('display', 'none'))
  })
}

watch(() => props.data, renderChart, { deep: true })
onMounted(() => {
  ro = new ResizeObserver(renderChart)
  ro.observe(containerRef.value)
  renderChart()
})
onUnmounted(() => ro?.disconnect())
</script>

<template>
  <div ref="containerRef" style="width:100%;overflow-x:auto">
    <div ref="svgRef" />
    <div
      ref="tooltipRef"
      class="chart-tooltip"
      style="display:none;position:fixed;z-index:9999;pointer-events:none"
    />
  </div>
</template>
