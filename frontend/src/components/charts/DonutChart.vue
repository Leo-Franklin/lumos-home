<!-- src/components/charts/DonutChart.vue -->
<script setup>
import { ref, watch, onMounted } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  data: { type: Array,   default: () => [] }, // [{ label: string, value: number, color: string }]
  size: { type: Number,  default: 160 },
  mini: { type: Boolean, default: false },    // hides legend
})

const svgRef = ref(null)

function renderChart() {
  if (!svgRef.value || !props.data.length) return
  d3.select(svgRef.value).selectAll('*').remove()

  const r     = props.size / 2
  const inner = props.mini ? r * 0.55 : r * 0.62

  const svg = d3.select(svgRef.value)
    .append('svg').attr('width', props.size).attr('height', props.size)
    .append('g').attr('transform', `translate(${r},${r})`)

  const pie     = d3.pie().value((d) => d.value).sort(null)
  const arc     = d3.arc().innerRadius(inner).outerRadius(r - 4)
  const arcHover = d3.arc().innerRadius(inner).outerRadius(r - 1)

  svg.selectAll('path').data(pie(props.data)).join('path')
    .attr('d', arc)
    .attr('fill', (d) => d.data.color)
    .attr('stroke', 'var(--color-bg, #161618)')
    .attr('stroke-width', 2)
    .style('cursor', 'pointer')
    .on('mouseenter', function() { d3.select(this).attr('d', arcHover) })
    .on('mouseleave', function() { d3.select(this).attr('d', arc) })

  // Total in center
  svg.append('text')
    .attr('text-anchor', 'middle').attr('dy', '0.35em')
    .attr('font-size', props.mini ? 14 : 20).attr('font-weight', 700)
    .attr('fill', 'var(--color-text-primary, #fff)')
    .text(d3.sum(props.data, (d) => d.value))
}

watch(() => [props.data, props.size, props.mini], renderChart, { deep: true })
onMounted(renderChart)
</script>

<template>
  <div class="donut-wrap">
    <div ref="svgRef" />
    <div v-if="!mini" class="donut-legend">
      <div v-for="item in data" :key="item.label" class="legend-item">
        <span class="legend-dot" :style="{ background: item.color }" />
        <span class="legend-label">{{ item.label }}</span>
        <span class="legend-value">{{ item.value }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.donut-wrap   { display: flex; align-items: center; gap: 24px; flex-wrap: wrap; }
.donut-legend { display: flex; flex-direction: column; gap: 8px; }
.legend-item  { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--color-text-secondary); }
.legend-dot   { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.legend-value { margin-left: auto; padding-left: 16px; font-weight: 600; color: var(--color-text-primary); }
</style>
