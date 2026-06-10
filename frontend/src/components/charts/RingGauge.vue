<!-- src/components/charts/RingGauge.vue -->
<script setup>
import { ref, watch, onMounted } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  value: { type: Number, default: 0 },
  size: { type: Number, default: 140 },
  label: { type: String, default: '' },
  color: { type: String, default: 'var(--color-primary)' },
})

const svgRef = ref(null)

function scoreColor(v) {
  if (v >= 85) return 'var(--color-online)'
  if (v >= 60) return 'var(--color-scanning)'
  return 'var(--color-warning)'
}

function render() {
  if (!svgRef.value) return
  d3.select(svgRef.value).selectAll('*').remove()

  const r = props.size / 2
  const stroke = Math.max(8, Math.round(props.size * 0.09))
  const radius = r - stroke
  const pct = Math.max(0, Math.min(100, props.value))
  const fill = scoreColor(pct)

  const svg = d3
    .select(svgRef.value)
    .append('svg')
    .attr('width', props.size)
    .attr('height', props.size)

  const g = svg.append('g').attr('transform', `translate(${r},${r})`)

  g.append('circle')
    .attr('r', radius)
    .attr('fill', 'none')
    .attr('stroke', 'var(--color-surface-overlay)')
    .attr('stroke-width', stroke)

  const arc = d3.arc().innerRadius(radius).outerRadius(radius).startAngle(0)
  g.append('path')
    .attr('d', arc.endAngle((pct / 100) * 2 * Math.PI))
    .attr('fill', 'none')
    .attr('stroke', fill)
    .attr('stroke-width', stroke)
    .attr('stroke-linecap', 'round')
    .attr('transform', 'rotate(-90)')

  g.append('text')
    .attr('text-anchor', 'middle')
    .attr('dy', '-0.1em')
    .attr('font-size', Math.round(props.size * 0.22))
    .attr('font-weight', 700)
    .attr('fill', 'var(--color-text-primary)')
    .attr('font-family', 'var(--font-display)')
    .text(`${Math.round(pct)}`)

  g.append('text')
    .attr('text-anchor', 'middle')
    .attr('dy', '1.4em')
    .attr('font-size', Math.round(props.size * 0.1))
    .attr('fill', 'var(--color-text-muted)')
    .text('%')
}

watch(() => [props.value, props.size], render)
onMounted(render)
</script>

<template>
  <div class="ring-gauge">
    <div ref="svgRef" />
    <div v-if="label" class="ring-label">{{ label }}</div>
  </div>
</template>

<style scoped>
.ring-gauge {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}
.ring-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  text-align: center;
  line-height: 1.4;
}
</style>
