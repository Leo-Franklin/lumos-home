<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as d3 from 'd3'
import api from '@/api/index'
import { Refresh, Histogram, FullScreen, Filter } from '@element-plus/icons-vue'
import { useDevicesStore } from '@/stores/devices'
import { useI18n } from 'vue-i18n'
import { useApiError } from '@/composables/useApiError'
import EmptyState from '@/components/EmptyState.vue'

const { t, locale } = useI18n()
const handleError = useApiError()
const devicesStore = useDevicesStore()

// ── Type config ──────────────────────────────────────────
// Colors reference --color-type-* tokens (see src/style.css and chartColors.js).
// d3 attr() accepts CSS var() strings; backgrounds use color-mix() to derive alpha tints.
// Labels are derived from t('common.deviceTypes.*') at render time via typeLabel().
const TYPE_CONFIG = {
  phone: { color: 'var(--color-type-phone)', icon: '📱' },
  computer: { color: 'var(--color-type-computer)', icon: '💻' },
  camera: { color: 'var(--color-type-camera)', icon: '📷' },
  iot: { color: 'var(--color-type-iot)', icon: '🔌' },
  router: { color: 'var(--color-type-router)', icon: '📡' },
  tablet: { color: 'var(--color-type-tablet)', icon: '📋' },
  tv: { color: 'var(--color-type-tv)', icon: '📺' },
  printer: { color: 'var(--color-type-printer)', icon: '🖨️' },
  smart_speaker: { color: 'var(--color-type-smart-speaker)', icon: '🔊' },
  game_console: { color: 'var(--color-type-game-console)', icon: '🎮' },
  nas: { color: 'var(--color-type-nas)', icon: '🗄️' },
  wearable: { color: 'var(--color-type-wearable)', icon: '⌚' },
  unknown: { color: 'var(--color-type-unknown)', icon: '⬡' },
}

const typeOf = (d) => TYPE_CONFIG[d.device_type] ?? TYPE_CONFIG.unknown

function typeLabel(type) {
  return t(`common.deviceTypes.${type || 'unknown'}`)
}

// ── State ────────────────────────────────────────────────
const svgEl = ref(null)
const canvasWrap = ref(null)
const loading = ref(false)
const nodes = ref([])
const selected = ref(null)
const hoveredMac = ref(null)
const activeTypes = ref([]) // empty = show all
const legendOpen = ref(true)
const tooltip = ref({ visible: false, x: 0, y: 0, node: null })

let zoomBehavior = null
let resizeObserver = null
let nodePositions = new Map()
let fitTransform = null

const ZOOM_MAX = 4

function computeGraphBounds(pos) {
  const pad = 56
  let minX = -pad
  let maxX = pad
  let minY = -pad
  let maxY = pad
  pos.forEach(({ x, y }) => {
    minX = Math.min(minX, x - 24)
    maxX = Math.max(maxX, x + 24)
    minY = Math.min(minY, y - 24)
    maxY = Math.max(maxY, y + 24)
  })
  return { minX, maxX, minY, maxY }
}

function computeFitTransform(W, H, pos, padding = 56) {
  const { minX, maxX, minY, maxY } = computeGraphBounds(pos)
  const bw = Math.max(maxX - minX, 120)
  const bh = Math.max(maxY - minY, 120)
  const cx = (minX + maxX) / 2
  const cy = (minY + maxY) / 2
  const scale = Math.min((W - padding * 2) / bw, (H - padding * 2) / bh, ZOOM_MAX)
  const transform = d3.zoomIdentity
    .translate(W / 2, H / 2)
    .scale(scale)
    .translate(-cx, -cy)
  return { transform, minScale: scale * 0.92, maxScale: ZOOM_MAX }
}

const stats = computed(() => {
  const total = nodes.value.length
  const online = nodes.value.filter((n) => n.is_online).length
  return {
    total,
    online,
    offline: total - online,
    rate: total ? Math.round((online / total) * 100) : 0,
  }
})

const typeStats = computed(() => {
  const counts = {}
  nodes.value.forEach((n) => {
    const t = n.device_type || 'unknown'
    counts[t] = (counts[t] || 0) + 1
  })
  return Object.entries(counts)
    .map(([type, count]) => ({ type, count, cfg: TYPE_CONFIG[type] ?? TYPE_CONFIG.unknown }))
    .sort((a, b) => b.count - a.count)
})

const visibleTypeCount = computed(() => typeStats.value.length)

// React to scan completion: reload topology when scan finishes
watch(
  () => devicesStore.scanning,
  (isScanning, wasScanning) => {
    if (wasScanning && !isScanning) loadTopology()
  },
)

watch(selected, () => updateSelectionHighlight())

function updateTooltipPosition(node) {
  if (!svgEl.value || !node) return
  const p = nodePositions.get(node.mac)
  if (!p) return
  const xf = d3.zoomTransform(svgEl.value)
  tooltip.value = {
    visible: true,
    x: xf.applyX(p.x) + 18,
    y: xf.applyY(p.y) - 14,
    node,
  }
}

function hideTooltip() {
  tooltip.value = { ...tooltip.value, visible: false }
}

function updateSelectionHighlight() {
  if (!svgEl.value) return
  d3.select(svgEl.value)
    .selectAll('g.dev')
    .each(function (d) {
      const isSel = selected.value?.mac === d.mac
      const isHover = hoveredMac.value === d.mac
      d3.select(this)
        .select('.sel-ring')
        .transition()
        .duration(180)
        .attr('r', isSel ? 17 : isHover ? 13 : 0)
        .attr('opacity', isSel ? 0.85 : isHover ? 0.45 : 0)
      d3.select(this)
        .select('.node-core')
        .transition()
        .duration(180)
        .attr('r', isSel ? 9 : d.is_online ? 7 : 5)
    })
}

// ── Data ─────────────────────────────────────────────────
async function loadTopology() {
  loading.value = true
  try {
    const { data } = await api.get('/devices/topology')
    nodes.value = data.nodes
    await nextTick()
    renderGraph()
  } catch (e) {
    handleError(e, 'topology.loadFailed')
  } finally {
    loading.value = false
  }
}

// ── Type filter ───────────────────────────────────────────
function toggleType(type) {
  const idx = activeTypes.value.indexOf(type)
  activeTypes.value =
    idx === -1 ? [...activeTypes.value, type] : activeTypes.value.filter((t) => t !== type)
  updateNodeOpacity()
}

function clearActiveTypes() {
  activeTypes.value = []
  updateNodeOpacity()
}

function updateNodeOpacity() {
  if (!svgEl.value) return
  const active = activeTypes.value
  d3.select(svgEl.value)
    .selectAll('g.dev')
    .transition()
    .duration(180)
    .attr('opacity', (d) => {
      if (active.length === 0) return 1
      return active.includes(d.device_type ?? 'unknown') ? 1 : 0.1
    })
  d3.select(svgEl.value)
    .selectAll('line')
    .transition()
    .duration(180)
    .attr('opacity', (d) => {
      const baseOpacity = d.is_online ? 0.22 : 0.09
      if (active.length === 0) return baseOpacity
      return active.includes(d.device_type ?? 'unknown') ? baseOpacity : 0.03
    })
}

// ── Render ───────────────────────────────────────────────
function renderGraph() {
  if (!svgEl.value) return

  const parent = svgEl.value.parentElement
  const W = parent.clientWidth
  const H = parent.clientHeight

  const svg = d3.select(svgEl.value)
  svg.selectAll('*').remove()
  svg.attr('width', W).attr('height', H)

  // Glow filter
  const defs = svg.append('defs')

  const gridPat = defs
    .append('pattern')
    .attr('id', 'topo-grid')
    .attr('width', 28)
    .attr('height', 28)
    .attr('patternUnits', 'userSpaceOnUse')
  gridPat
    .append('circle')
    .attr('cx', 1)
    .attr('cy', 1)
    .attr('r', 0.65)
    .attr('fill', 'var(--color-border-subtle)')

  const vignette = defs
    .append('radialGradient')
    .attr('id', 'topo-vignette')
    .attr('cx', '50%')
    .attr('cy', '50%')
    .attr('r', '55%')
  vignette
    .append('stop')
    .attr('offset', '0%')
    .attr('stop-color', 'var(--color-primary)')
    .attr('stop-opacity', 0.06)
  vignette
    .append('stop')
    .attr('offset', '100%')
    .attr('stop-color', 'var(--color-bg)')
    .attr('stop-opacity', 0.35)

  const flt = defs
    .append('filter')
    .attr('id', 'topo-glow')
    .attr('x', '-50%')
    .attr('y', '-50%')
    .attr('width', '200%')
    .attr('height', '200%')
  flt.append('feGaussianBlur').attr('stdDeviation', 2.5).attr('result', 'blur')
  const fm = flt.append('feMerge')
  fm.append('feMergeNode').attr('in', 'blur')
  fm.append('feMergeNode').attr('in', 'SourceGraphic')

  const fltSel = defs
    .append('filter')
    .attr('id', 'topo-glow-strong')
    .attr('x', '-80%')
    .attr('y', '-80%')
    .attr('width', '260%')
    .attr('height', '260%')
  fltSel.append('feGaussianBlur').attr('stdDeviation', 4).attr('result', 'blur')
  const fmSel = fltSel.append('feMerge')
  fmSel.append('feMergeNode').attr('in', 'blur')
  fmSel.append('feMergeNode').attr('in', 'SourceGraphic')

  const g = svg.append('g')

  g.append('rect')
    .attr('x', -W * 3)
    .attr('y', -H * 3)
    .attr('width', W * 6)
    .attr('height', H * 6)
    .attr('fill', 'url(#topo-grid)')
    .attr('opacity', 0.45)
  g.append('rect')
    .attr('x', -W * 3)
    .attr('y', -H * 3)
    .attr('width', W * 6)
    .attr('height', H * 6)
    .attr('fill', 'url(#topo-vignette)')

  const graphG = g.append('g')

  // Zoom / pan — scale limits are set after layout; default centers on viewport
  zoomBehavior = d3.zoom().on('zoom', (e) => {
    g.attr('transform', e.transform)
    if (tooltip.value.visible && tooltip.value.node) {
      updateTooltipPosition(tooltip.value.node)
    }
  })
  zoomBehavior.scaleExtent([0.5, ZOOM_MAX])
  svg.call(zoomBehavior)
  fitTransform = d3.zoomIdentity.translate(W / 2, H / 2)
  svg.call(zoomBehavior.transform, fitTransform)
  svg.on('click', (event) => {
    if (event.target === svgEl.value) selected.value = null
  })

  if (!nodes.value.length) return

  // Build type groups
  const typeGroups = {}
  nodes.value.forEach((n) => {
    const t = n.device_type || 'unknown'
    ;(typeGroups[t] = typeGroups[t] || []).push(n)
  })
  const typeKeys = Object.keys(typeGroups)
  const nTypes = typeKeys.length

  const typeAngle = Object.fromEntries(
    typeKeys.map((t, i) => [t, (2 * Math.PI * i) / nTypes - Math.PI / 2]),
  )

  // Radial ring distance, scales gently with total node count
  const RADIAL_R = Math.max(220, Math.min(340, nodes.value.length * 5))
  const SLOT = 34 // px per node slot (diameter + gap)

  // ── Structured warm-start positions ──
  // Each type group is spread across one or more concentric arcs
  // within its sector, so the force simulation starts without overlap.
  const initPos = new Map()
  typeKeys.forEach((type) => {
    const devs = typeGroups[type]
    const M = devs.length
    const angle = typeAngle[type]
    const sectorSpan = Math.min(((2 * Math.PI) / nTypes) * 0.72, Math.PI * 1.25)

    let placed = 0,
      ring = 0
    while (placed < M) {
      const r = RADIAL_R + ring * 46
      const cap = Math.max(1, Math.floor((sectorSpan * r) / SLOT))
      const n = Math.min(cap, M - placed)
      const span = n === 1 ? 0 : sectorSpan * (n / cap)
      for (let j = 0; j < n; j++) {
        const da = n === 1 ? angle : angle - span / 2 + (span * j) / (n - 1)
        initPos.set(devs[placed + j].mac, { x: r * Math.cos(da), y: r * Math.sin(da) })
      }
      placed += n
      ring++
    }
  })

  // ── Force simulation for collision resolution ──
  const simNodes = nodes.value.map((n) => {
    const p = initPos.get(n.mac)
    return {
      id: n.mac,
      data: n,
      group: n.device_type || 'unknown',
      targetAngle: typeAngle[n.device_type || 'unknown'] ?? 0,
      x: p.x,
      y: p.y,
      vx: 0,
      vy: 0,
    }
  })
  const gwNode = { id: '__gw__', fx: 0, fy: 0 }
  const allSimNodes = [gwNode, ...simNodes]
  const simLinks = simNodes.map((n) => ({ source: '__gw__', target: n.id }))

  function makeAngularForce() {
    let ns = []
    function force(alpha) {
      ns.forEach((n) => {
        if (n.fx !== undefined) return
        const tx = RADIAL_R * Math.cos(n.targetAngle)
        const ty = RADIAL_R * Math.sin(n.targetAngle)
        n.vx += (tx - n.x) * 0.06 * alpha
        n.vy += (ty - n.y) * 0.06 * alpha
      })
    }
    force.initialize = (nodes) => {
      ns = nodes
    }
    return force
  }

  const simulation = d3
    .forceSimulation(allSimNodes)
    .force(
      'link',
      d3
        .forceLink(simLinks)
        .id((d) => d.id)
        .distance(RADIAL_R)
        .strength(0.03),
    )
    .force('charge', d3.forceManyBody().strength(-45))
    .force('collision', d3.forceCollide(16).strength(1))
    .force('radial', d3.forceRadial(RADIAL_R, 0, 0).strength(0.18))
    .force('angular', makeAngularForce())
    .stop()

  for (let i = 0; i < 300; i++) simulation.tick()

  const pos = new Map(simNodes.map((n) => [n.id, { x: n.x, y: n.y }]))
  nodePositions = pos

  const fit = computeFitTransform(W, H, pos)
  fitTransform = fit.transform
  zoomBehavior.scaleExtent([fit.minScale, fit.maxScale])
  svg.call(zoomBehavior.transform, fitTransform)

  // ── Connection lines ──
  graphG
    .append('g')
    .attr('class', 'links')
    .selectAll('line')
    .data(nodes.value)
    .join('line')
    .attr('class', (d) => (d.is_online ? 'link-online' : 'link-offline'))
    .attr('x1', 0)
    .attr('y1', 0)
    .attr('x2', (d) => pos.get(d.mac).x)
    .attr('y2', (d) => pos.get(d.mac).y)
    .attr('stroke', (d) => typeOf(d).color)
    .attr('stroke-width', (d) => (d.is_online ? 0.9 : 0.6))
    .attr('opacity', 0)
    .transition()
    .duration(600)
    .delay((_, i) => 80 + i * 12)
    .attr('opacity', (d) => (d.is_online ? 0.22 : 0.08))

  // ── Group labels (at cluster centroid) ──
  typeKeys.forEach((type) => {
    const group = simNodes.filter((n) => n.group === type)
    if (!group.length) return
    const cx = d3.mean(group, (n) => n.x)
    const cy = d3.mean(group, (n) => n.y)
    const angle = Math.atan2(cy, cx)
    const dist = Math.hypot(cx, cy)
    const cfg = TYPE_CONFIG[type] || TYPE_CONFIG.unknown

    graphG
      .append('text')
      .attr('x', (dist + 40) * Math.cos(angle))
      .attr('y', (dist + 40) * Math.sin(angle))
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'middle')
      .attr('font-size', '11px')
      .attr('font-weight', 700)
      .attr('letter-spacing', '0.07em')
      .attr('fill', cfg.color)
      .attr('opacity', 0.65)
      .attr('pointer-events', 'none')
      .text(`${typeLabel(type).toUpperCase()} · ${group.length}`)
  })

  // ── Device nodes ──
  const nodeG = graphG
    .append('g')
    .selectAll('g.dev')
    .data(nodes.value)
    .join('g')
    .attr('class', 'dev')
    .attr('transform', (d) => {
      const p = pos.get(d.mac)
      return `translate(${p.x},${p.y}) scale(0)`
    })
    .style('cursor', 'pointer')
    .on('click', (event, d) => {
      event.stopPropagation()
      selected.value = d
    })
    .on('mouseover', (_, d) => {
      hoveredMac.value = d.mac
      updateTooltipPosition(d)
      updateSelectionHighlight()
    })
    .on('mouseout', () => {
      hoveredMac.value = null
      hideTooltip()
      updateSelectionHighlight()
    })

  nodeG
    .transition()
    .duration(500)
    .delay((_, i) => 120 + i * 18)
    .attr('transform', (d) => {
      const p = pos.get(d.mac)
      return `translate(${p.x},${p.y}) scale(1)`
    })

  // Selection / hover ring
  nodeG
    .append('circle')
    .attr('class', 'sel-ring')
    .attr('r', 0)
    .attr('fill', 'none')
    .attr('stroke', (d) => typeOf(d).color)
    .attr('stroke-width', 1.5)
    .attr('opacity', 0)

  // Glow halo (online only)
  nodeG
    .filter((d) => d.is_online)
    .append('circle')
    .attr('class', 'node-halo')
    .attr('r', 14)
    .attr('fill', (d) => typeOf(d).color)
    .attr('opacity', 0.12)
    .attr('filter', 'url(#topo-glow)')

  // Main circle
  nodeG
    .append('circle')
    .attr('class', 'node-core')
    .attr('r', (d) => (d.is_online ? 7 : 5))
    .attr('fill', (d) => (d.is_online ? typeOf(d).color : 'transparent'))
    .attr('stroke', (d) => typeOf(d).color)
    .attr('stroke-width', (d) => (d.is_online ? 0 : 1.5))
    .attr('opacity', (d) => (d.is_online ? 0.95 : 0.45))

  // ── Gateway node (center) ──
  const gwG = graphG.append('g').attr('class', 'gateway')
  const pulse1 = gwG
    .append('circle')
    .attr('class', 'gw-pulse')
    .attr('r', 32)
    .attr('fill', 'none')
    .attr('stroke', 'var(--color-primary)')
    .attr('stroke-width', 1)
    .attr('opacity', 0.35)
  pulse1
    .append('animate')
    .attr('attributeName', 'r')
    .attr('values', '28;48;28')
    .attr('dur', '3.2s')
    .attr('repeatCount', 'indefinite')
  pulse1
    .append('animate')
    .attr('attributeName', 'opacity')
    .attr('values', '0.35;0.05;0.35')
    .attr('dur', '3.2s')
    .attr('repeatCount', 'indefinite')
  const pulse2 = gwG
    .append('circle')
    .attr('class', 'gw-pulse')
    .attr('r', 32)
    .attr('fill', 'none')
    .attr('stroke', 'var(--color-primary)')
    .attr('stroke-width', 0.6)
    .attr('opacity', 0.2)
  pulse2
    .append('animate')
    .attr('attributeName', 'r')
    .attr('values', '28;56;28')
    .attr('dur', '3.2s')
    .attr('begin', '1.6s')
    .attr('repeatCount', 'indefinite')
  pulse2
    .append('animate')
    .attr('attributeName', 'opacity')
    .attr('values', '0.25;0;0.25')
    .attr('dur', '3.2s')
    .attr('begin', '1.6s')
    .attr('repeatCount', 'indefinite')
  gwG
    .append('circle')
    .attr('r', 38)
    .attr('fill', 'var(--color-primary)')
    .attr('opacity', 0.08)
    .attr('filter', 'url(#topo-glow-strong)')
  gwG
    .append('circle')
    .attr('r', 24)
    .attr('fill', 'var(--color-bg)')
    .attr('stroke', 'var(--color-primary)')
    .attr('stroke-width', 2)
  gwG
    .append('circle')
    .attr('r', 30)
    .attr('fill', 'none')
    .attr('stroke', 'var(--color-primary)')
    .attr('stroke-width', 1)
    .attr('opacity', 0.25)
  gwG
    .append('text')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('font-size', '18px')
    .attr('pointer-events', 'none')
    .text('🏠')
  gwG
    .append('text')
    .attr('y', 42)
    .attr('text-anchor', 'middle')
    .attr('font-size', '10px')
    .attr('fill', 'var(--color-text-secondary)')
    .attr('font-weight', 600)
    .attr('letter-spacing', '0.06em')
    .attr('pointer-events', 'none')
    .text(t('topology.gatewayLabel').toUpperCase())

  if (activeTypes.value.length > 0) updateNodeOpacity()
  updateSelectionHighlight()
}

// ── Zoom controls ─────────────────────────────────────────
function zoomIn() {
  d3.select(svgEl.value).transition().duration(300).call(zoomBehavior.scaleBy, 1.4)
}
function zoomOut() {
  d3.select(svgEl.value).transition().duration(300).call(zoomBehavior.scaleBy, 0.7)
}
function resetZoom() {
  if (!svgEl.value || !zoomBehavior || !fitTransform) return
  d3.select(svgEl.value).transition().duration(400).call(zoomBehavior.transform, fitTransform)
}

// ── Helpers ───────────────────────────────────────────────
function latencyColor(ms) {
  return ms < 5 ? 'var(--color-online)' : ms < 30 ? 'var(--color-scanning)' : 'var(--color-warning)'
}

function formatTime(v) {
  if (!v) return '—'
  return new Date(v).toLocaleString(locale.value, { hour12: false })
}

function avatarInitial(name) {
  return name ? name.slice(0, 1).toUpperCase() : '?'
}

onMounted(() => {
  loadTopology()
  if (canvasWrap.value && typeof ResizeObserver !== 'undefined') {
    let resizeTimer = null
    resizeObserver = new ResizeObserver(() => {
      clearTimeout(resizeTimer)
      resizeTimer = setTimeout(() => {
        if (nodes.value.length) renderGraph()
      }, 150)
    })
    resizeObserver.observe(canvasWrap.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})
</script>

<template>
  <div class="topo-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-main">
        <div class="header-top-row">
          <h2 class="page-title">{{ $t('topology.title') }}</h2>
          <div v-if="nodes.length" class="inline-stats">
            <span class="stat-pill stat-pill--online">
              <span class="stat-dot" />
              <span class="stat-val tabular-nums">{{ stats.online }}/{{ stats.total }}</span>
              <span class="stat-lbl">{{ $t('topology.kpiOnline') }}</span>
            </span>
            <span class="stat-pill">
              <span class="stat-val tabular-nums">{{ stats.offline }}</span>
              <span class="stat-lbl">{{ $t('topology.kpiOffline') }}</span>
            </span>
            <span class="stat-pill">
              <span class="stat-val tabular-nums">{{ visibleTypeCount }}</span>
              <span class="stat-lbl">{{ $t('topology.kpiTypes') }}</span>
            </span>
            <span class="stat-pill stat-pill--rate">
              <span class="stat-val tabular-nums">{{ stats.rate }}%</span>
              <span class="stat-lbl">{{ $t('topology.kpiRate') }}</span>
              <span class="stat-mini-bar">
                <span class="stat-mini-fill" :style="{ width: stats.rate + '%' }" />
              </span>
            </span>
          </div>
        </div>
        <span class="page-sub">
          <template v-if="!nodes.length">{{ $t('topology.subtitle') }}</template>
          <template v-else>{{ $t('topology.canvasHint') }}</template>
          <span v-if="devicesStore.scanning" class="scanning-tag"
            >● {{ $t('topology.scanning') }}</span
          >
        </span>
      </div>
      <div class="header-actions">
        <el-button
          :loading="devicesStore.scanning"
          :icon="Histogram"
          size="small"
          type="primary"
          @click="devicesStore.scan()"
        >
          {{ $t('topology.scanNetwork') }}
        </el-button>
        <el-button :loading="loading" :icon="Refresh" size="small" @click="loadTopology">
          {{ $t('topology.refresh') }}
        </el-button>
      </div>
    </div>

    <!-- Canvas + Detail panel -->
    <div class="topo-body">
      <div ref="canvasWrap" class="canvas-wrap glass-card" v-loading="loading">
        <svg ref="svgEl" class="topo-svg" />

        <!-- Hover tooltip -->
        <transition name="tt-pop">
          <div
            v-if="tooltip.visible && tooltip.node"
            class="node-tooltip glass-card"
            :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
          >
            <span class="tt-icon">{{ typeOf(tooltip.node).icon }}</span>
            <div class="tt-body">
              <span class="tt-name">{{
                tooltip.node.alias || tooltip.node.hostname || tooltip.node.ip || tooltip.node.mac
              }}</span>
              <span class="tt-meta">
                <span class="tt-type">{{ typeLabel(tooltip.node.device_type) }}</span>
                <span class="tt-sep">·</span>
                <span
                  class="tt-status"
                  :class="tooltip.node.is_online ? 'tt-online' : 'tt-offline'"
                  >{{
                    tooltip.node.is_online ? $t('topology.online') : $t('topology.offline')
                  }}</span
                >
                <template v-if="tooltip.node.is_online && tooltip.node.response_time_ms != null">
                  <span class="tt-sep">·</span>
                  <span
                    class="tt-lat"
                    :style="{ color: latencyColor(tooltip.node.response_time_ms) }"
                  >
                    {{ Math.round(tooltip.node.response_time_ms) }}ms
                  </span>
                </template>
              </span>
            </div>
          </div>
        </transition>

        <!-- Zoom controls -->
        <div class="zoom-controls glass-card">
          <button class="zoom-btn" :aria-label="$t('topology.zoomIn')" @click="zoomIn">+</button>
          <div class="zoom-divider" />
          <button
            class="zoom-btn"
            :aria-label="$t('topology.resetView')"
            :title="$t('topology.resetView')"
            @click="resetZoom"
          >
            <el-icon><FullScreen /></el-icon>
          </button>
          <div class="zoom-divider" />
          <button class="zoom-btn" :aria-label="$t('topology.zoomOut')" @click="zoomOut">−</button>
        </div>

        <!-- Legend (interactive filter) -->
        <div class="legend glass-card" :class="{ collapsed: !legendOpen }">
          <button
            class="legend-toggle"
            type="button"
            :aria-expanded="legendOpen"
            @click="legendOpen = !legendOpen"
          >
            <el-icon><Filter /></el-icon>
            <span>{{ $t('topology.filterLegend') }}</span>
            <span v-if="activeTypes.length" class="filter-count">{{ activeTypes.length }}</span>
            <span class="legend-chevron" :class="{ open: legendOpen }">›</span>
          </button>
          <transition name="legend-expand">
            <div v-show="legendOpen" class="legend-body">
              <div
                v-for="item in typeStats"
                :key="item.type"
                class="legend-item"
                :class="{
                  active: activeTypes.includes(item.type),
                  dimmed: activeTypes.length > 0 && !activeTypes.includes(item.type),
                }"
                @click="toggleType(item.type)"
              >
                <span class="legend-dot" :style="{ background: item.cfg.color }" />
                <span class="legend-label">{{ typeLabel(item.type) }}</span>
                <span class="legend-count tabular-nums">{{ item.count }}</span>
              </div>
              <div
                v-if="activeTypes.length > 0"
                class="legend-item legend-clear"
                @click="clearActiveTypes"
              >
                ✕ {{ $t('topology.clear') }}
              </div>
            </div>
          </transition>
        </div>

        <!-- Empty state -->
        <div v-if="!loading && nodes.length === 0" class="topology-empty">
          <EmptyState
            icon="topology"
            :title="$t('common.empty.topology.title')"
            :description="$t('common.empty.topology.description')"
            :action-label="$t('common.empty.topology.action')"
            @action="devicesStore.scan()"
          />
        </div>
      </div>

      <!-- Detail panel -->
      <transition name="panel-slide">
        <div
          v-if="selected"
          class="detail-panel glass-card"
          :style="{ '--panel-accent': typeOf(selected).color }"
        >
          <div class="panel-accent-bar" />
          <div class="panel-head">
            <span
              class="type-badge"
              :style="{
                background: `color-mix(in srgb, ${typeOf(selected).color} 12%, transparent)`,
                color: typeOf(selected).color,
              }"
            >
              {{ typeOf(selected).icon }} {{ typeLabel(selected.device_type) }}
            </span>
            <button class="close-btn" :aria-label="$t('common.close')" @click="selected = null">
              ✕
            </button>
          </div>

          <div class="panel-name">
            {{ selected.alias || selected.hostname || selected.ip || selected.mac }}
          </div>

          <div class="panel-status-row">
            <span
              class="status-dot"
              :class="selected.is_online ? 'online' : 'offline'"
              role="status"
              :aria-label="selected.is_online ? $t('topology.online') : $t('topology.offline')"
            />
            <span class="status-text">{{
              selected.is_online ? $t('topology.online') : $t('topology.offline')
            }}</span>
            <span
              v-if="selected.is_online && selected.response_time_ms != null"
              class="latency"
              :style="{ color: latencyColor(selected.response_time_ms) }"
            >
              {{ Math.round(selected.response_time_ms) }}ms
            </span>
          </div>

          <div class="info-section">
            <div class="info-row">
              <span class="il">{{ $t('topology.mac') }}</span
              ><span class="iv mono">{{ selected.mac }}</span>
            </div>
            <div class="info-row">
              <span class="il">{{ $t('topology.ip') }}</span
              ><span class="iv mono">{{ selected.ip || '—' }}</span>
            </div>
            <div class="info-row">
              <span class="il">{{ $t('topology.hostname') }}</span
              ><span class="iv mono">{{ selected.hostname || '—' }}</span>
            </div>
            <div class="info-row">
              <span class="il">{{ $t('topology.vendor') }}</span
              ><span class="iv">{{ selected.vendor || '—' }}</span>
            </div>
            <div class="info-row">
              <span class="il">{{ $t('topology.lastSeen') }}</span
              ><span class="iv">{{ formatTime(selected.last_seen) }}</span>
            </div>
          </div>

          <div v-if="selected.owners?.length" class="info-section">
            <div class="section-title">{{ $t('topology.owners') }}</div>
            <div v-for="owner in selected.owners" :key="owner.id" class="owner-row">
              <!-- Avatar -->
              <div class="owner-avatar" :class="owner.is_home ? 'home' : 'away'">
                <img
                  v-if="owner.avatar_url"
                  :src="owner.avatar_url"
                  :alt="owner.name"
                  class="avatar-img"
                />
                <span v-else class="avatar-initial">{{ avatarInitial(owner.name) }}</span>
              </div>
              <span class="owner-name">{{ owner.name }}</span>
              <span class="owner-tag" :class="owner.is_home ? 'tag-home' : 'tag-away'">
                {{ owner.is_home ? $t('topology.atHome') : $t('topology.away') }}
              </span>
            </div>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<style scoped>
.topo-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* ── Header ─────────────────────────────── */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
  flex-shrink: 0;
  gap: var(--space-3);
}
.header-main {
  min-width: 0;
  flex: 1;
}
.header-top-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-bottom: 2px;
}
.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
  flex-shrink: 0;
}
.inline-stats {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}
.stat-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-surface-raised);
  font-size: 11px;
  line-height: 1;
}
.stat-pill--online {
  border-color: color-mix(in srgb, var(--color-online) 30%, transparent);
  background: color-mix(in srgb, var(--color-online) 8%, var(--color-surface-raised));
}
.stat-pill--rate {
  gap: 6px;
  padding-right: 8px;
}
.stat-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-online);
  flex-shrink: 0;
  animation: breathe 2s ease-in-out infinite;
}
.stat-val {
  font-weight: 700;
  color: var(--color-text-primary);
  font-size: 12px;
}
.stat-lbl {
  color: var(--color-text-muted);
  font-size: 10px;
}
.stat-mini-bar {
  width: 36px;
  height: 3px;
  border-radius: var(--radius-full);
  background: var(--color-border-subtle);
  overflow: hidden;
  flex-shrink: 0;
}
.stat-mini-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--color-online), var(--color-primary));
  transition: width 0.5s var(--easing-standard);
}
.page-sub {
  font-size: 11px;
  color: var(--color-text-muted);
}
.scanning-tag {
  color: var(--color-scanning);
  animation: blink 1.2s ease-in-out infinite;
  margin-left: 6px;
}
@keyframes blink {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}
@keyframes breathe {
  0%,
  100% {
    opacity: 1;
    box-shadow: 0 0 5px color-mix(in srgb, var(--color-online) 50%, transparent);
  }
  50% {
    opacity: 0.45;
    box-shadow: 0 0 12px color-mix(in srgb, var(--color-online) 80%, transparent);
  }
}
.header-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
  align-self: flex-start;
}

/* ── Body ───────────────────────────────── */
.topo-body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: var(--space-3);
  overflow: hidden;
}

/* ── Canvas ─────────────────────────────── */
.canvas-wrap {
  flex: 1;
  position: relative;
  overflow: hidden;
  min-height: 0;
}
.canvas-wrap svg,
.topo-svg {
  display: block;
  width: 100%;
  height: 100%;
}

/* ── Tooltip ────────────────────────────── */
.node-tooltip {
  position: absolute;
  pointer-events: none;
  padding: 8px 10px;
  font-size: 11px;
  z-index: 10;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  max-width: 260px;
  box-shadow: var(--shadow-lg);
}
.tt-icon {
  font-size: 16px;
  line-height: 1;
  flex-shrink: 0;
}
.tt-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.tt-name {
  color: var(--color-text-primary);
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tt-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  color: var(--color-text-secondary);
}
.tt-type {
  font-size: 10px;
  color: var(--color-text-muted);
}
.tt-sep {
  color: var(--color-text-muted);
}
.tt-online {
  color: var(--color-online);
  font-weight: 600;
}
.tt-offline {
  color: var(--color-offline);
}
.tt-lat {
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 10px;
}

.tt-pop-enter-active {
  transition:
    opacity 0.15s ease,
    transform 0.15s var(--easing-snap);
}
.tt-pop-leave-active {
  transition: opacity 0.1s ease;
}
.tt-pop-enter-from {
  opacity: 0;
  transform: translateY(4px) scale(0.96);
}
.tt-pop-leave-to {
  opacity: 0;
}

/* Zoom controls */
.zoom-controls {
  position: absolute;
  bottom: 16px;
  right: 16px;
  display: flex;
  flex-direction: column;
  padding: 4px;
  gap: 2px;
  z-index: 8;
}
.zoom-divider {
  height: 1px;
  margin: 2px 4px;
  background: var(--color-border-subtle);
}
.zoom-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    background var(--duration-fast) ease,
    color var(--duration-fast) ease,
    transform var(--duration-fast) var(--easing-snap);
}
.zoom-btn:hover {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
}
.zoom-btn:active {
  transform: scale(0.92);
}

/* Legend */
.legend {
  position: absolute;
  bottom: 16px;
  left: 16px;
  z-index: 8;
  max-width: min(320px, calc(100% - 120px));
  overflow: hidden;
}
.legend.collapsed {
  max-width: 220px;
}
.legend-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 8px 12px;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  text-align: left;
}
.legend-toggle:hover {
  color: var(--color-text-primary);
}
.filter-count {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  background: var(--color-primary-subtle);
  color: var(--color-primary);
}
.legend-chevron {
  display: inline-block;
  margin-left: auto;
  transform: rotate(90deg);
  transition: transform 0.2s ease;
  font-size: 14px;
  color: var(--color-text-muted);
}
.legend-chevron.open {
  transform: rotate(-90deg);
}
.legend-body {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 0 10px 10px;
  max-height: 140px;
  overflow-y: auto;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-full);
  border: 1px solid transparent;
  transition: all 0.15s ease;
  user-select: none;
}
.legend-item:hover {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
  transform: translateY(-1px);
}
.legend-item.active {
  background: var(--color-primary-subtle);
  border-color: var(--color-primary-border);
  color: var(--color-text-primary);
}
.legend-item.dimmed {
  opacity: 0.35;
}
.legend-clear {
  color: var(--color-text-muted);
  font-size: 10px;
  width: 100%;
  justify-content: center;
}
.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 6px color-mix(in srgb, currentColor 40%, transparent);
}
.legend-label {
  flex: 1;
  min-width: 0;
}
.legend-count {
  font-size: 10px;
  font-weight: 700;
  color: var(--color-text-muted);
  font-family: var(--font-display);
}

.legend-expand-enter-active,
.legend-expand-leave-active {
  transition:
    opacity 0.2s ease,
    max-height 0.25s ease;
  overflow: hidden;
}
.legend-expand-enter-from,
.legend-expand-leave-to {
  opacity: 0;
  max-height: 0;
}

/* Empty state */
.topo-page :deep(.topology-empty) {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: auto;
}

.topo-page :deep(.topology-empty .empty-state) {
  pointer-events: auto;
}

/* ── Detail panel ───────────────────────── */
.detail-panel {
  position: relative;
  width: 288px;
  flex-shrink: 0;
  padding: 16px;
  overflow-y: auto;
  overflow-x: hidden;
}
.panel-accent-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(
    90deg,
    var(--panel-accent, var(--color-primary)),
    color-mix(in srgb, var(--panel-accent, var(--color-primary)) 30%, transparent)
  );
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
}

.panel-slide-enter-active {
  transition:
    opacity 0.25s ease,
    transform 0.3s var(--easing-snap);
}
.panel-slide-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.2s ease;
}
.panel-slide-enter-from,
.panel-slide-leave-to {
  opacity: 0;
  transform: translateX(24px) scale(0.98);
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.type-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: var(--radius-full);
}
.close-btn {
  background: none;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: 12px;
  padding: 2px 5px;
  border-radius: 4px;
  line-height: 1;
}
.close-btn:hover {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
}

.panel-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 10px;
  word-break: break-all;
}

.panel-status-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 14px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-dot.online {
  background: var(--color-online);
  box-shadow: 0 0 5px color-mix(in srgb, var(--color-online) 50%, transparent);
  animation: breathe 2s ease-in-out infinite;
}
.status-dot.offline {
  background: var(--color-offline);
}
.latency {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
}

.info-section {
  margin-bottom: 14px;
}
.section-title {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-text-muted);
  margin-bottom: 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--color-border-subtle, var(--color-border));
}
.info-row {
  display: flex;
  gap: 6px;
  align-items: baseline;
  margin-bottom: 5px;
}
.il {
  min-width: 52px;
  font-size: 11px;
  color: var(--color-text-muted);
  flex-shrink: 0;
}
.iv {
  font-size: 12px;
  color: var(--color-text-primary);
  word-break: break-all;
}
.iv.mono {
  font-family: var(--font-mono);
  font-size: 11px;
}

/* ── Member card ────────────────────────── */
.owner-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 9px;
}
.owner-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  flex-shrink: 0;
  border: 2px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  font-size: 12px;
  font-weight: 600;
}
.owner-avatar.home {
  border-color: var(--color-online);
  background: var(--color-primary-subtle);
  color: var(--color-online);
}
.owner-avatar.away {
  border-color: var(--color-border);
  background: var(--color-surface-raised);
  color: var(--color-text-muted);
}
.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.owner-name {
  font-size: 13px;
  color: var(--color-text-primary);
  font-weight: 500;
}
.owner-tag {
  margin-left: auto;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: var(--radius-full);
  font-weight: 600;
}
.tag-home {
  background: var(--color-primary-subtle);
  color: var(--color-online);
}
.tag-away {
  background: var(--color-surface-raised);
  color: var(--color-text-muted);
}

@media (max-width: 768px) {
  .topo-body {
    flex-direction: column;
  }
  .detail-panel {
    width: 100%;
    max-height: 40vh;
  }
  .legend {
    max-width: calc(100% - 80px);
  }
  .inline-stats {
    width: 100%;
  }
}

@media (max-width: 520px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }
  .header-actions {
    align-self: stretch;
    justify-content: flex-end;
  }
  .stat-pill--rate .stat-mini-bar {
    display: none;
  }
}
</style>

<!-- D3-generated SVG elements need unscoped styles -->
<style>
.topo-svg line.link-online {
  stroke-dasharray: 6 10;
  animation: topo-flow 1.8s linear infinite;
}
.topo-svg line.link-offline {
  stroke-dasharray: 3 6;
  opacity: 0.08;
}
@keyframes topo-flow {
  to {
    stroke-dashoffset: -16;
  }
}
</style>
