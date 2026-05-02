<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import * as d3 from 'd3'
import api from '@/api/index'
import { ElMessage } from 'element-plus'
import { Refresh, Histogram } from '@element-plus/icons-vue'
import { useDevicesStore } from '@/stores/devices'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const devicesStore = useDevicesStore()

// ── Type config ──────────────────────────────────────────
const TYPE_CONFIG = {
  phone:         { color: '#F2C94C', label: '手机',    icon: '📱' },
  computer:      { color: '#26C281', label: '电脑',    icon: '💻' },
  camera:        { color: '#5E5CE6', label: '摄像头',  icon: '📷' },
  iot:           { color: '#F07D38', label: 'IoT',     icon: '🔌' },
  router:        { color: '#06B6D4', label: '路由器',  icon: '📡' },
  tablet:        { color: '#D946EF', label: '平板',    icon: '📋' },
  tv:            { color: '#7C3AED', label: '电视',    icon: '📺' },
  printer:       { color: '#14B8A6', label: '打印机',  icon: '🖨️' },
  smart_speaker: { color: '#A3E635', label: '智能音箱', icon: '🔊' },
  game_console:  { color: '#EF4444', label: '游戏机',  icon: '🎮' },
  nas:           { color: '#60A5FA', label: 'NAS',     icon: '🗄️' },
  wearable:      { color: '#FB7185', label: '可穿戴',  icon: '⌚' },
  unknown:       { color: '#8B8B96', label: '未知',    icon: '⬡'  },
}

const typeOf = (d) => TYPE_CONFIG[d.device_type] ?? TYPE_CONFIG.unknown

// ── State ────────────────────────────────────────────────
const svgEl      = ref(null)
const loading    = ref(false)
const nodes      = ref([])
const selected   = ref(null)
const activeTypes = ref([])   // empty = show all
const tooltip    = ref({ visible: false, x: 0, y: 0, node: null })

let zoomBehavior = null

const stats = computed(() => ({
  total:  nodes.value.length,
  online: nodes.value.filter(n => n.is_online).length,
}))

// React to scan completion: reload topology when scan finishes
watch(() => devicesStore.scanning, (isScanning, wasScanning) => {
  if (wasScanning && !isScanning) loadTopology()
})

// ── Data ─────────────────────────────────────────────────
async function loadTopology() {
  loading.value = true
  try {
    const { data } = await api.get('/devices/topology')
    nodes.value = data.nodes
    await nextTick()
    renderGraph()
  } catch {
    ElMessage.error(t('topology.loadFailed'))
  } finally {
    loading.value = false
  }
}

// ── Type filter ───────────────────────────────────────────
function toggleType(type) {
  const idx = activeTypes.value.indexOf(type)
  activeTypes.value = idx === -1
    ? [...activeTypes.value, type]
    : activeTypes.value.filter(t => t !== type)
  updateNodeOpacity()
}

function updateNodeOpacity() {
  if (!svgEl.value) return
  const active = activeTypes.value
  d3.select(svgEl.value).selectAll('g.dev')
    .transition().duration(180)
    .attr('opacity', d => {
      if (active.length === 0) return 1
      return active.includes(d.device_type ?? 'unknown') ? 1 : 0.1
    })
  d3.select(svgEl.value).selectAll('line')
    .transition().duration(180)
    .attr('opacity', d => {
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
  const flt  = defs.append('filter').attr('id', 'topo-glow')
    .attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%')
  flt.append('feGaussianBlur').attr('stdDeviation', 2.5).attr('result', 'blur')
  const fm = flt.append('feMerge')
  fm.append('feMergeNode').attr('in', 'blur')
  fm.append('feMergeNode').attr('in', 'SourceGraphic')

  const g = svg.append('g')

  // Zoom / pan
  zoomBehavior = d3.zoom()
    .scaleExtent([0.1, 6])
    .on('zoom', e => g.attr('transform', e.transform))
  svg.call(zoomBehavior)
  svg.call(zoomBehavior.transform, d3.zoomIdentity.translate(W / 2, H / 2))

  if (!nodes.value.length) return

  // Build type groups
  const typeGroups = {}
  nodes.value.forEach(n => {
    const t = n.device_type || 'unknown'
    ;(typeGroups[t] = typeGroups[t] || []).push(n)
  })
  const typeKeys = Object.keys(typeGroups)
  const nTypes = typeKeys.length

  const typeAngle = Object.fromEntries(
    typeKeys.map((t, i) => [t, (2 * Math.PI * i) / nTypes - Math.PI / 2])
  )

  // Radial ring distance, scales gently with total node count
  const RADIAL_R = Math.max(220, Math.min(340, nodes.value.length * 5))
  const SLOT = 34  // px per node slot (diameter + gap)

  // ── Structured warm-start positions ──
  // Each type group is spread across one or more concentric arcs
  // within its sector, so the force simulation starts without overlap.
  const initPos = new Map()
  typeKeys.forEach(type => {
    const devs  = typeGroups[type]
    const M     = devs.length
    const angle = typeAngle[type]
    const sectorSpan = Math.min((2 * Math.PI / nTypes) * 0.72, Math.PI * 1.25)

    let placed = 0, ring = 0
    while (placed < M) {
      const r   = RADIAL_R + ring * 46
      const cap = Math.max(1, Math.floor((sectorSpan * r) / SLOT))
      const n   = Math.min(cap, M - placed)
      const span = n === 1 ? 0 : sectorSpan * (n / cap)
      for (let j = 0; j < n; j++) {
        const da = n === 1 ? angle : angle - span / 2 + span * j / (n - 1)
        initPos.set(devs[placed + j].mac, { x: r * Math.cos(da), y: r * Math.sin(da) })
      }
      placed += n
      ring++
    }
  })

  // ── Force simulation for collision resolution ──
  const simNodes = nodes.value.map(n => {
    const p = initPos.get(n.mac)
    return { id: n.mac, data: n, group: n.device_type || 'unknown',
             targetAngle: typeAngle[n.device_type || 'unknown'] ?? 0,
             x: p.x, y: p.y, vx: 0, vy: 0 }
  })
  const gwNode = { id: '__gw__', fx: 0, fy: 0 }
  const allSimNodes = [gwNode, ...simNodes]
  const simLinks = simNodes.map(n => ({ source: '__gw__', target: n.id }))

  function makeAngularForce() {
    let ns = []
    function force(alpha) {
      ns.forEach(n => {
        if (n.fx !== undefined) return
        const tx = RADIAL_R * Math.cos(n.targetAngle)
        const ty = RADIAL_R * Math.sin(n.targetAngle)
        n.vx += (tx - n.x) * 0.06 * alpha
        n.vy += (ty - n.y) * 0.06 * alpha
      })
    }
    force.initialize = nodes => { ns = nodes }
    return force
  }

  const simulation = d3.forceSimulation(allSimNodes)
    .force('link',     d3.forceLink(simLinks).id(d => d.id).distance(RADIAL_R).strength(0.03))
    .force('charge',   d3.forceManyBody().strength(-45))
    .force('collision', d3.forceCollide(16).strength(1))
    .force('radial',   d3.forceRadial(RADIAL_R, 0, 0).strength(0.18))
    .force('angular',  makeAngularForce())
    .stop()

  for (let i = 0; i < 300; i++) simulation.tick()

  const pos = new Map(simNodes.map(n => [n.id, { x: n.x, y: n.y }]))

  // ── Connection lines ──
  g.append('g').selectAll('line')
    .data(nodes.value)
    .join('line')
    .attr('x1', 0).attr('y1', 0)
    .attr('x2', d => pos.get(d.mac).x)
    .attr('y2', d => pos.get(d.mac).y)
    .attr('stroke', d => typeOf(d).color)
    .attr('stroke-width', 0.7)
    .attr('stroke-dasharray', d => d.is_online ? 'none' : '4,3')
    .attr('opacity',           d => d.is_online ? 0.14 : 0.06)

  // ── Group labels (at cluster centroid) ──
  typeKeys.forEach(type => {
    const group = simNodes.filter(n => n.group === type)
    if (!group.length) return
    const cx    = d3.mean(group, n => n.x)
    const cy    = d3.mean(group, n => n.y)
    const angle = Math.atan2(cy, cx)
    const dist  = Math.hypot(cx, cy)
    const cfg   = TYPE_CONFIG[type] || TYPE_CONFIG.unknown

    g.append('text')
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
      .text(`${t(`common.deviceTypes.${type}`).toUpperCase()} · ${group.length}`)
  })

  // ── Device nodes ──
  const nodeG = g.append('g').selectAll('g.dev')
    .data(nodes.value)
    .join('g')
    .attr('class', 'dev')
    .attr('transform', d => { const p = pos.get(d.mac); return `translate(${p.x},${p.y})` })
    .style('cursor', 'pointer')
    .on('click', (_, d) => { selected.value = d })
    .on('mouseover', (_, d) => {
      const p  = pos.get(d.mac)
      const xf = d3.zoomTransform(svgEl.value)
      tooltip.value = { visible: true, x: xf.applyX(p.x) + 16, y: xf.applyY(p.y) - 10, node: d }
    })
    .on('mouseout', () => { tooltip.value = { ...tooltip.value, visible: false } })

  // Glow halo (online only — small, won't bleed into neighbours)
  nodeG.filter(d => d.is_online)
    .append('circle')
    .attr('r', 14)
    .attr('fill', d => typeOf(d).color)
    .attr('opacity', 0.1)
    .attr('filter', 'url(#topo-glow)')

  // Main circle
  nodeG.append('circle')
    .attr('r', d => d.is_online ? 7 : 5)
    .attr('fill',   d => d.is_online ? typeOf(d).color : 'transparent')
    .attr('stroke', d => typeOf(d).color)
    .attr('stroke-width', d => d.is_online ? 0 : 1.5)
    .attr('opacity', d => d.is_online ? 0.9 : 0.4)

  // ── Gateway node (center) ──
  const gwG = g.append('g').attr('class', 'gateway')
  gwG.append('circle')
    .attr('r', 38).attr('fill', '#5E5CE6').attr('opacity', 0.07)
    .attr('filter', 'url(#topo-glow)')
  gwG.append('circle')
    .attr('r', 24).attr('fill', '#1a1a2e')
    .attr('stroke', '#5E5CE6').attr('stroke-width', 2)
  gwG.append('circle')
    .attr('r', 30).attr('fill', 'none')
    .attr('stroke', '#5E5CE6').attr('stroke-width', 1).attr('opacity', 0.2)
  gwG.append('text')
    .attr('text-anchor', 'middle').attr('dominant-baseline', 'central')
    .attr('font-size', '18px').attr('pointer-events', 'none').text('🏠')
  gwG.append('text')
    .attr('y', 40).attr('text-anchor', 'middle')
    .attr('font-size', '11px').attr('fill', '#9898b8').attr('font-weight', 600)
    .attr('pointer-events', 'none').text(t('topology.gatewayLabel'))

  if (activeTypes.value.length > 0) updateNodeOpacity()
}

// ── Zoom controls ─────────────────────────────────────────
function zoomIn()  { d3.select(svgEl.value).transition().duration(300).call(zoomBehavior.scaleBy, 1.4) }
function zoomOut() { d3.select(svgEl.value).transition().duration(300).call(zoomBehavior.scaleBy, 0.7) }
function resetZoom() {
  if (!svgEl.value) return
  const parent = svgEl.value.parentElement
  d3.select(svgEl.value).transition().duration(400).call(
    zoomBehavior.transform,
    d3.zoomIdentity.translate(parent.clientWidth / 2, parent.clientHeight / 2),
  )
}

// ── Helpers ───────────────────────────────────────────────
function latencyColor(ms) {
  return ms < 5 ? '#26C281' : ms < 30 ? '#F2C94C' : '#F07D38'
}

function formatTime(v) {
  return v ? new Date(v).toLocaleString('zh-CN', { hour12: false }) : '—'
}

function avatarInitial(name) {
  return name ? name.slice(0, 1).toUpperCase() : '?'
}

onMounted(loadTopology)
</script>

<template>
  <div class="topo-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ $t('topology.title') }}</h2>
        <span class="page-sub">
          {{ $t('topology.onlineCount', { online: stats.online, total: stats.total }) }}
          <span v-if="devicesStore.scanning" class="scanning-tag">● {{ $t('topology.scanning') }}</span>
        </span>
      </div>
      <div class="header-actions">
        <el-button
          :loading="devicesStore.scanning"
          :icon="Histogram"
          size="small"
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
      <div class="canvas-wrap" v-loading="loading">
        <svg ref="svgEl" />

        <!-- Hover tooltip -->
        <transition name="tt-fade">
          <div
            v-if="tooltip.visible && tooltip.node"
            class="node-tooltip"
            :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
          >
            <span class="tt-name">{{ tooltip.node.alias || tooltip.node.hostname || tooltip.node.ip || tooltip.node.mac }}</span>
            <span class="tt-sep">·</span>
            <span
              class="tt-status"
              :class="tooltip.node.is_online ? 'tt-online' : 'tt-offline'"
            >{{ tooltip.node.is_online ? $t('topology.online') : $t('topology.offline') }}</span>
            <template v-if="tooltip.node.is_online && tooltip.node.response_time_ms != null">
              <span class="tt-sep">·</span>
              <span class="tt-lat" :style="{ color: latencyColor(tooltip.node.response_time_ms) }">
                {{ Math.round(tooltip.node.response_time_ms) }}ms
              </span>
            </template>
          </div>
        </transition>

        <!-- Zoom controls -->
        <div class="zoom-controls">
          <button class="zoom-btn" @click="zoomIn">+</button>
          <button class="zoom-btn" @click="resetZoom" title="重置视角">⊙</button>
          <button class="zoom-btn" @click="zoomOut">−</button>
        </div>

        <!-- Legend (interactive filter) -->
        <div class="legend">
          <div
            v-for="(cfg, key) in TYPE_CONFIG"
            :key="key"
            class="legend-item"
            :class="{ active: activeTypes.includes(key), dimmed: activeTypes.length > 0 && !activeTypes.includes(key) }"
            @click="toggleType(key)"
          >
            <span class="legend-dot" :style="{ background: cfg.color }" />
            <span>{{ $t(`common.deviceTypes.${key}`) }}</span>
          </div>
          <div
            v-if="activeTypes.length > 0"
            class="legend-item legend-clear"
            @click="activeTypes = []; updateNodeOpacity()"
          >
            ✕ {{ $t('topology.clear') }}
          </div>
        </div>

        <!-- Empty state -->
        <div v-if="!loading && nodes.length === 0" class="empty-hint">
          {{ $t('topology.noDevices') }}
        </div>
      </div>

      <!-- Detail panel -->
      <transition name="panel-slide">
        <div v-if="selected" class="detail-panel">
          <div class="panel-head">
            <span
              class="type-badge"
              :style="{ background: typeOf(selected).color + '20', color: typeOf(selected).color }"
            >
              {{ typeOf(selected).icon }} {{ $t(`common.deviceTypes.${selected.device_type || 'unknown'}`) }}
            </span>
            <button class="close-btn" @click="selected = null">✕</button>
          </div>

          <div class="panel-name">
            {{ selected.alias || selected.hostname || selected.ip || selected.mac }}
          </div>

          <div class="panel-status-row">
            <span class="status-dot" :class="selected.is_online ? 'online' : 'offline'" />
            <span class="status-text">{{ selected.is_online ? $t('topology.online') : $t('topology.offline') }}</span>
            <span
              v-if="selected.is_online && selected.response_time_ms != null"
              class="latency"
              :style="{ color: latencyColor(selected.response_time_ms) }"
            >
              {{ Math.round(selected.response_time_ms) }}ms
            </span>
          </div>

          <div class="info-section">
            <div class="info-row"><span class="il">{{ $t('topology.mac') }}</span><span class="iv mono">{{ selected.mac }}</span></div>
            <div class="info-row"><span class="il">{{ $t('topology.ip') }}</span><span class="iv mono">{{ selected.ip || '—' }}</span></div>
            <div class="info-row"><span class="il">{{ $t('topology.hostname') }}</span><span class="iv mono">{{ selected.hostname || '—' }}</span></div>
            <div class="info-row"><span class="il">{{ $t('topology.vendor') }}</span><span class="iv">{{ selected.vendor || '—' }}</span></div>
            <div class="info-row"><span class="il">{{ $t('topology.lastSeen') }}</span><span class="iv">{{ formatTime(selected.last_seen) }}</span></div>
          </div>

          <div v-if="selected.owners?.length" class="info-section">
            <div class="section-title">{{ $t('topology.owners') }}</div>
            <div v-for="owner in selected.owners" :key="owner.id" class="owner-row">
              <!-- Avatar -->
              <div class="owner-avatar" :class="owner.is_home ? 'home' : 'away'">
                <img v-if="owner.avatar_url" :src="owner.avatar_url" :alt="owner.name" class="avatar-img" />
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
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-shrink: 0;
}
.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 2px;
}
.page-sub {
  font-size: 12px;
  color: var(--color-text-muted);
}
.scanning-tag {
  color: #F2C94C;
  animation: blink 1.2s ease-in-out infinite;
  margin-left: 6px;
}
@keyframes blink {
  0%, 100% { opacity: 1 }
  50% { opacity: 0.35 }
}
.header-actions {
  display: flex;
  gap: 8px;
}

/* ── Body ───────────────────────────────── */
.topo-body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 12px;
  overflow: hidden;
}

/* ── Canvas ─────────────────────────────── */
.canvas-wrap {
  flex: 1;
  position: relative;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  overflow: hidden;
}
.canvas-wrap svg {
  display: block;
  width: 100%;
  height: 100%;
}

/* ── Tooltip ────────────────────────────── */
.node-tooltip {
  position: absolute;
  pointer-events: none;
  background: rgba(20, 20, 36, 0.92);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 5px 9px;
  font-size: 11px;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 5px;
  z-index: 10;
  backdrop-filter: blur(4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
}
.tt-name   { color: var(--color-text-primary); font-weight: 500; }
.tt-sep    { color: var(--color-text-muted); }
.tt-online { color: var(--color-online); }
.tt-offline{ color: var(--color-offline); }
.tt-lat    { font-family: var(--font-mono); font-weight: 600; }

.tt-fade-enter-active,
.tt-fade-leave-active { transition: opacity 0.1s ease; }
.tt-fade-enter-from,
.tt-fade-leave-to  { opacity: 0; }

/* Zoom controls */
.zoom-controls {
  position: absolute;
  bottom: 16px;
  right: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.zoom-btn {
  width: 28px;
  height: 28px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-raised);
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.12s;
}
.zoom-btn:hover {
  background: var(--color-surface-overlay);
  color: var(--color-text-primary);
}

/* Legend */
.legend {
  position: absolute;
  bottom: 16px;
  left: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 3px 7px;
  border-radius: var(--radius-full);
  border: 1px solid transparent;
  transition: all 0.15s ease;
  user-select: none;
}
.legend-item:hover {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
}
.legend-item.active {
  background: var(--color-surface-raised);
  border-color: var(--color-border);
  color: var(--color-text-primary);
}
.legend-item.dimmed {
  opacity: 0.4;
}
.legend-clear {
  color: var(--color-text-muted);
  font-size: 10px;
}
.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* Empty hint */
.empty-hint {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--color-text-muted);
  pointer-events: none;
}

/* ── Detail panel ───────────────────────── */
.detail-panel {
  width: 268px;
  flex-shrink: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  padding: 16px;
  overflow-y: auto;
}

.panel-slide-enter-active,
.panel-slide-leave-active { transition: all 0.2s ease; }
.panel-slide-enter-from,
.panel-slide-leave-to { opacity: 0; transform: translateX(20px); }

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
.status-dot.online  { background: var(--color-online); box-shadow: 0 0 5px rgba(38, 194, 129, 0.5); }
.status-dot.offline { background: var(--color-offline); }
.latency {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
}

.info-section { margin-bottom: 14px; }
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
  background: rgba(38, 194, 129, 0.1);
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
  background: rgba(38, 194, 129, 0.12);
  color: var(--color-online);
}
.tag-away {
  background: var(--color-surface-raised);
  color: var(--color-text-muted);
}
</style>
