<!-- src/components/charts/LineChart.vue -->
<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  data:    { type: Array,    default: () => [] }, // [{ x: Date|string, y: number }]
  color:   { type: String,   default: '#5E5CE6' },
  height:  { type: Number,   default: 160 },
  // mini=true: hides all axes for sparkline use
  mini:    { type: Boolean,  default: false },
  xFormat: { type: Function, default: null },  // custom tick formatter, e.g. d3.timeFormat('%m/%d')
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
    : { top: 10, right: 16, bottom: 32, left: 44 }
  const w = W - m.left - m.right
  const h = H - m.top  - m.bottom

  const rootSvg = d3.select(svgRef.value)
    .append('svg').attr('width', W).attr('height', H)
  const g = rootSvg.append('g').attr('transform', `translate(${m.left},${m.top})`)

  const xVals = props.data.map((d) => (d.x instanceof Date ? d.x : new Date(d.x)))
  // When there's only one data point, extent returns [same, same] → zero-width domain.
  // Pad by ±12 hours so the single point renders centered as a dot.
  let [xMin, xMax] = d3.extent(xVals)
  if (xMin.getTime() === xMax.getTime()) {
    xMin = new Date(xMin.getTime() - 12 * 3600 * 1000)
    xMax = new Date(xMax.getTime() + 12 * 3600 * 1000)
  }
  const x = d3.scaleTime().domain([xMin, xMax]).range([0, w])
  const y = d3.scaleLinear()
    .domain([0, (d3.max(props.data, (d) => d.y) || 1) * 1.1])
    .range([h, 0])

  // Gradient
  const gradId = `lg-${Math.random().toString(36).slice(2, 7)}`
  const defs = rootSvg.append('defs')
  const grad = defs.append('linearGradient').attr('id', gradId).attr('x2', '0').attr('y2', '1')
  grad.append('stop').attr('offset', '0%')  .attr('stop-color', props.color).attr('stop-opacity', 0.35)
  grad.append('stop').attr('offset', '100%').attr('stop-color', props.color).attr('stop-opacity', 0.02)

  // Area fill
  g.append('path')
    .datum(props.data)
    .attr('fill', `url(#${gradId})`)
    .attr('d', d3.area()
      .x((d, i) => x(xVals[i]))
      .y0(h).y1((d) => y(d.y))
      .curve(d3.curveMonotoneX))

  // Line
  g.append('path')
    .datum(props.data)
    .attr('fill', 'none')
    .attr('stroke', props.color)
    .attr('stroke-width', 1.5)
    .attr('d', d3.line()
      .x((d, i) => x(xVals[i]))
      .y((d) => y(d.y))
      .curve(d3.curveMonotoneX))

  if (props.mini) return

  g.append('g')
    .attr('transform', `translate(0,${h})`)
    .call(d3.axisBottom(x).ticks(5).tickFormat(props.xFormat ?? d3.timeFormat('%m/%d')))
    .call((ax) => { ax.select('.domain').remove(); ax.selectAll('line').attr('stroke', '#444') })
    .selectAll('text').attr('fill', '#888').attr('font-size', 10)

  g.append('g')
    .call(d3.axisLeft(y).ticks(4).tickSize(-w))
    .call((ax) => {
      ax.select('.domain').remove()
      ax.selectAll('.tick line').attr('stroke', '#2a2a30').attr('stroke-dasharray', '3,3')
      ax.selectAll('.tick text').attr('fill', '#888').attr('font-size', 10)
    })
}

watch(() => [props.data, props.height, props.color], renderChart, { deep: true })
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
