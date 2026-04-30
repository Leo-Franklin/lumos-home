<!-- src/components/charts/BarChart.vue -->
<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  // vertical / horizontal: [{ label: string, value: number, color?: string, valueLabel?: string }]
  // grouped:               [{ label: string, [groupKey]: number }]
  data:    { type: Array,    default: () => [] },
  mode:    { type: String,   default: 'vertical' }, // 'vertical'|'horizontal'|'grouped'
  color:   { type: String,   default: '#5E5CE6' },
  // grouped only: [{ key: 'camera', color: '#5E5CE6', label: '摄像头' }, ...]
  groups:  { type: Array,    default: () => [] },
  height:  { type: Number,   default: 200 },
  mini:    { type: Boolean,  default: false },
  // optional: (value: number) => cssColorString — overrides per-bar color in vertical/horizontal
  colorFn: { type: Function, default: null },
  // horizontal mode: outer wrapper clips at this height and becomes scrollable
  scrollMaxHeight: { type: Number, default: 380 },
})

const containerRef = ref(null)
const svgRef       = ref(null)
let ro = null

const ROW_H = 26 // min px per item in horizontal mode

// Scrollable wrapper style — only for horizontal mode with many items
const scrollWrapStyle = computed(() => {
  if (props.mode === 'horizontal' && !props.mini) {
    return {
      maxHeight:   `${props.scrollMaxHeight}px`,
      overflowY:   'auto',
      overflowX:   'hidden',
    }
  }
  return {}
})

function computeH() {
  if (props.mode === 'horizontal' && !props.mini) {
    return Math.max(props.height, props.data.length * ROW_H)
  }
  return props.height
}

function renderChart() {
  if (!svgRef.value || !containerRef.value || !props.data.length) return
  d3.select(svgRef.value).selectAll('*').remove()

  // Subtract 4px to leave room for the thin scrollbar in horizontal mode
  const W = (containerRef.value.clientWidth || 400) - (props.mode === 'horizontal' && !props.mini ? 4 : 0)
  const H = computeH()
  const m = props.mini
    ? { top: 4, right: 4, bottom: 4, left: 4 }
    : props.mode === 'horizontal'
      ? { top: 10, right: 64, bottom: 20, left: 120 }
      : { top: 10, right: 16, bottom: 36, left: 44 }

  const w = W - m.left - m.right
  const h = H - m.top  - m.bottom

  const svg = d3.select(svgRef.value)
    .append('svg').attr('width', W).attr('height', H)
    .append('g').attr('transform', `translate(${m.left},${m.top})`)

  if      (props.mode === 'horizontal') renderHorizontal(svg, w, h)
  else if (props.mode === 'grouped')    renderGrouped(svg, w, h)
  else                                  renderVertical(svg, w, h)
}

function barColor(d) {
  return props.colorFn ? props.colorFn(d.value) : (d.color || props.color)
}

function renderVertical(svg, w, h) {
  const x = d3.scaleBand().domain(props.data.map((d) => d.label)).range([0, w]).padding(0.25)
  const y = d3.scaleLinear()
    .domain([0, (d3.max(props.data, (d) => d.value) || 1) * 1.1])
    .range([h, 0])

  svg.selectAll('rect').data(props.data).join('rect')
    .attr('x', (d) => x(d.label))
    .attr('y', (d) => y(d.value))
    .attr('width',  x.bandwidth())
    .attr('height', (d) => h - y(d.value))
    .attr('rx', 3)
    .attr('fill', (d) => barColor(d))

  if (props.mini) return

  svg.append('g').attr('transform', `translate(0,${h})`)
    .call(d3.axisBottom(x).tickSize(0))
    .call((ax) => ax.select('.domain').attr('stroke', '#333'))
    .selectAll('text').attr('fill', '#888').attr('font-size', 10)

  svg.append('g')
    .call(d3.axisLeft(y).ticks(4).tickSize(-w))
    .call((ax) => {
      ax.select('.domain').remove()
      ax.selectAll('.tick line').attr('stroke', '#2a2a30').attr('stroke-dasharray', '3,3')
      ax.selectAll('.tick text').attr('fill', '#888').attr('font-size', 10)
    })
}

function renderHorizontal(svg, w, h) {
  const n = props.data.length
  // Shrink font for very dense lists
  const fontSize = n > 100 ? 9 : n > 50 ? 10 : 11
  // Truncate labels that would overflow the left margin
  const truncate = (s) => s.length > 15 ? s.slice(0, 14) + '…' : s

  const y = d3.scaleBand()
    .domain(props.data.map((d) => d.label))
    .range([0, h])
    .padding(0.3)
  const x = d3.scaleLinear()
    .domain([0, (d3.max(props.data, (d) => d.value) || 1) * 1.1])
    .range([0, w])

  // Subtle background track
  svg.selectAll('.bg-track').data(props.data).join('rect')
    .attr('class', 'bg-track')
    .attr('y', (d) => y(d.label))
    .attr('x', 0)
    .attr('height', y.bandwidth())
    .attr('width', w)
    .attr('rx', 3)
    .attr('fill', 'rgba(255,255,255,0.03)')

  // Value bar
  svg.selectAll('.bar').data(props.data).join('rect')
    .attr('class', 'bar')
    .attr('y', (d) => y(d.label))
    .attr('x', 0)
    .attr('height', y.bandwidth())
    .attr('width',  (d) => Math.max(0, x(d.value)))
    .attr('rx', 3)
    .attr('fill', (d) => barColor(d))

  // Value label to the right
  svg.selectAll('.vl').data(props.data).join('text')
    .attr('class', 'vl')
    .attr('y', (d) => y(d.label) + y.bandwidth() / 2 + 4)
    .attr('x', (d) => x(d.value) + 6)
    .attr('font-size', fontSize)
    .attr('fill', '#888')
    .text((d) => d.valueLabel ?? d.value)

  if (props.mini) return

  svg.append('g')
    .call(d3.axisLeft(y).tickSize(0).tickFormat(truncate))
    .call((ax) => ax.select('.domain').remove())
    .selectAll('text')
    .attr('fill', '#aaa')
    .attr('font-size', fontSize)
}

function renderGrouped(svg, w, h) {
  const keys = props.groups.map((g) => g.key)
  const x0 = d3.scaleBand().domain(props.data.map((d) => d.label)).range([0, w]).padding(0.2)
  const x1 = d3.scaleBand().domain(keys).range([0, x0.bandwidth()]).padding(0.05)
  const maxY = (d3.max(props.data, (d) => d3.max(keys, (k) => d[k] ?? 0)) || 1) * 1.1
  const y    = d3.scaleLinear().domain([0, maxY]).range([h, 0])

  props.groups.forEach((grp) => {
    svg.selectAll(`.bar-${grp.key}`).data(props.data).join('rect')
      .attr('class', `bar-${grp.key}`)
      .attr('x',      (d) => x0(d.label) + x1(grp.key))
      .attr('y',      (d) => y(d[grp.key] ?? 0))
      .attr('width',  x1.bandwidth())
      .attr('height', (d) => h - y(d[grp.key] ?? 0))
      .attr('rx', 2)
      .attr('fill', grp.color)
  })

  if (props.mini) return

  svg.append('g').attr('transform', `translate(0,${h})`)
    .call(d3.axisBottom(x0).tickSize(0))
    .call((ax) => ax.select('.domain').attr('stroke', '#333'))
    .selectAll('text').attr('fill', '#888').attr('font-size', 10)

  svg.append('g')
    .call(d3.axisLeft(y).ticks(4).tickSize(-w))
    .call((ax) => {
      ax.select('.domain').remove()
      ax.selectAll('.tick line').attr('stroke', '#2a2a30').attr('stroke-dasharray', '3,3')
      ax.selectAll('.tick text').attr('fill', '#888').attr('font-size', 10)
    })
}

watch(() => [props.data, props.height, props.mode, props.groups], renderChart, { deep: true })
onMounted(() => {
  ro = new ResizeObserver(renderChart)
  ro.observe(containerRef.value)
  renderChart()
})
onUnmounted(() => ro?.disconnect())
</script>

<template>
  <div ref="containerRef" style="width:100%">
    <div :style="scrollWrapStyle" class="bar-scroll">
      <div ref="svgRef" />
    </div>
  </div>
</template>

<style scoped>
.bar-scroll {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.12) transparent;
}
.bar-scroll::-webkit-scrollbar {
  width: 4px;
}
.bar-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.bar-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 2px;
}
.bar-scroll::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.22);
}
</style>
