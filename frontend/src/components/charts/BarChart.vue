<!-- src/components/charts/BarChart.vue -->
<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
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
})

const containerRef = ref(null)
const svgRef       = ref(null)
let ro = null

function renderChart() {
  if (!svgRef.value || !containerRef.value || !props.data.length) return
  d3.select(svgRef.value).selectAll('*').remove()

  const W = containerRef.value.clientWidth || 400
  const H = props.height
  const m = props.mini
    ? { top: 4, right: 4, bottom: 4, left: 4 }
    : props.mode === 'horizontal'
      ? { top: 10, right: 64, bottom: 20, left: 110 }
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
  const y = d3.scaleBand().domain(props.data.map((d) => d.label)).range([0, h]).padding(0.25)
  const x = d3.scaleLinear()
    .domain([0, (d3.max(props.data, (d) => d.value) || 1) * 1.1])
    .range([0, w])

  svg.selectAll('rect').data(props.data).join('rect')
    .attr('y', (d) => y(d.label))
    .attr('x', 0)
    .attr('height', y.bandwidth())
    .attr('width',  (d) => x(d.value))
    .attr('rx', 3)
    .attr('fill', (d) => barColor(d))

  // Value labels on the right of each bar
  svg.selectAll('.vl').data(props.data).join('text')
    .attr('class', 'vl')
    .attr('y', (d) => y(d.label) + y.bandwidth() / 2 + 4)
    .attr('x', (d) => x(d.value) + 6)
    .attr('font-size', 11).attr('fill', '#888')
    .text((d) => d.valueLabel ?? d.value)

  if (props.mini) return

  svg.append('g')
    .call(d3.axisLeft(y).tickSize(0))
    .call((ax) => ax.select('.domain').remove())
    .selectAll('text').attr('fill', '#aaa').attr('font-size', 11)
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

watch(() => [props.data, props.height, props.mode], renderChart, { deep: true })
onMounted(() => {
  ro = new ResizeObserver(renderChart)
  ro.observe(containerRef.value)
  renderChart()
})
onUnmounted(() => ro?.disconnect())
</script>

<template>
  <div ref="containerRef" style="width:100%">
    <div ref="svgRef" />
  </div>
</template>
