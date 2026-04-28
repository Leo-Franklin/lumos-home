<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import * as d3 from 'd3'
import api from '@/api/index'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'

// ── Type config ──────────────────────────────────────────
const TYPE_CONFIG = {
  phone:    { color: '#F2C94C', label: '手机',   icon: '📱' },
  computer: { color: '#26C281', label: '电脑',   icon: '💻' },
  camera:   { color: '#5E5CE6', label: '摄像头', icon: '📷' },
  iot:      { color: '#F07D38', label: 'IoT',    icon: '🔌' },
  unknown:  { color: '#8B8B96', label: '未知',   icon: '⬡'  },
}

const typeOf = (d) => TYPE_CONFIG[d.device_type] ?? TYPE_CONFIG.unknown

// ── State ────────────────────────────────────────────────
const svgEl   = ref(null)
const loading = ref(false)
const nodes   = ref([])
const selected = ref(null)

let zoomBehavior = null

const stats = computed(() => ({
  total:  nodes.value.length,
  online: nodes.value.filter(n => n.is_online).length,
}))

// ── Data ─────────────────────────────────────────────────
async function loadTopology() {
  loading.value = true
  try {
    const { data } = await api.get('/devices/topology')
    nodes.value = data.nodes
    await nextTick()
    renderGraph()
  } catch {
    ElMessage.error('加载拓扑数据失败')
  } finally {
    loading.value = false
  }
}

// ── Layout ───────────────────────────────────────────────
function computePositions(allNodes) {
  const byType = {}
  allNodes.forEach(n => {
    const t = n.device_type || 'unknown'
    ;(byType[t] = byType[t] || []).push(n)
  })

  const types = Object.keys(byType)
  const N = types.length || 1
  const R1 = Math.max(210, N * 80)  // ring radius for group centers
  const R2 = 85                      // sub-ring radius for devices in a group

  const pos = new Map()
  const groupMeta = []

  types.forEach((type, i) => {
    const a  = (2 * Math.PI * i) / N - Math.PI / 2
    const gx = R1 * Math.cos(a)
    const gy = R1 * Math.sin(a)
    groupMeta.push({ type, x: gx, y: gy, a })

    const devs = byType[type]
    const M    = devs.length

    devs.forEach((dev, j) => {
      if (M === 1) {
        pos.set(dev.mac, { x: gx, y: gy })
      } else {
        const span = Math.min(Math.PI * 0.85, 0.5 * M)
        const da   = a - span / 2 + span * j / (M - 1)
        pos.set(dev.mac, {
          x: gx + R2 * Math.cos(da),
          y: gy + R2 * Math.sin(da),
        })
      }
    })
  })

  return { pos, groupMeta }
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
    .attr('x', '-60%').attr('y', '-60%').attr('width', '220%').attr('height', '220%')
  flt.append('feGaussianBlur').attr('stdDeviation', 3.5).attr('result', 'blur')
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

  const { pos, groupMeta } = computePositions(nodes.value)

  // ── Connection lines ──
  g.append('g').selectAll('line')
    .data(nodes.value)
    .join('line')
    .attr('x1', 0).attr('y1', 0)
    .attr('x2', d => pos.get(d.mac).x)
    .attr('y2', d => pos.get(d.mac).y)
    .attr('stroke', d => typeOf(d).color)
    .attr('stroke-width', 1)
    .attr('stroke-dasharray', d => d.is_online ? 'none' : '5,4')
    .attr('opacity',           d => d.is_online ? 0.22 : 0.09)

  // ── Group labels ──
  groupMeta.forEach(grp => {
    const dist     = Math.hypot(grp.x, grp.y)
    const labelDist = dist + 58
    const lx = labelDist * Math.cos(grp.a)
    const ly = labelDist * Math.sin(grp.a)
    const cfg = TYPE_CONFIG[grp.type] || TYPE_CONFIG.unknown

    g.append('text')
      .attr('x', lx).attr('y', ly)
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'middle')
      .attr('font-size', '10px')
      .attr('font-weight', 700)
      .attr('letter-spacing', '0.08em')
      .attr('fill', cfg.color)
      .attr('opacity', 0.75)
      .attr('pointer-events', 'none')
      .text(cfg.label.toUpperCase())
  })

  // ── Device nodes ──
  const nodeG = g.append('g').selectAll('g.dev')
    .data(nodes.value)
    .join('g')
    .attr('class', 'dev')
    .attr('transform', d => { const p = pos.get(d.mac); return `translate(${p.x},${p.y})` })
    .style('cursor', 'pointer')
    .on('click', (_, d) => { selected.value = d })

  // Glow halo (online)
  nodeG.filter(d => d.is_online)
    .append('circle')
    .attr('r', 24)
    .attr('fill', d => typeOf(d).color)
    .attr('opacity', 0.12)
    .attr('filter', 'url(#topo-glow)')

  // Pulse ring (online)
  nodeG.filter(d => d.is_online)
    .append('circle')
    .attr('r', 18)
    .attr('fill', 'none')
    .attr('stroke', d => typeOf(d).color)
    .attr('stroke-width', 1.5)
    .attr('opacity', 0.4)

  // Main body
  nodeG.append('circle')
    .attr('r', 13)
    .attr('fill',   d => d.is_online ? typeOf(d).color : '#252535')
    .attr('stroke', d => typeOf(d).color)
    .attr('stroke-width', d => d.is_online ? 0 : 1.5)
    .attr('opacity', d => d.is_online ? 1 : 0.55)

  // Type icon
  nodeG.append('text')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('font-size', '11px')
    .attr('pointer-events', 'none')
    .text(d => typeOf(d).icon)

  // Device name
  nodeG.append('text')
    .attr('y', 26)
    .attr('text-anchor', 'middle')
    .attr('font-size', '10px')
    .attr('fill', '#c8c8d8')
    .attr('font-weight', 500)
    .attr('pointer-events', 'none')
    .text(d => (d.alias || d.hostname || d.ip || d.mac.slice(-5)).slice(0, 13))

  // Latency badge
  nodeG.filter(d => d.is_online && d.response_time_ms != null)
    .append('text')
    .attr('y', 38)
    .attr('text-anchor', 'middle')
    .attr('font-size', '9px')
    .attr('pointer-events', 'none')
    .attr('fill', d => {
      const ms = d.response_time_ms
      return ms < 5 ? '#26C281' : ms < 30 ? '#F2C94C' : '#F07D38'
    })
    .text(d => `${Math.round(d.response_time_ms)}ms`)

  // Owner label (above node)
  nodeG.filter(d => d.owners?.length > 0)
    .append('text')
    .attr('y', -23)
    .attr('text-anchor', 'middle')
    .attr('font-size', '9px')
    .attr('fill', '#8888a8')
    .attr('pointer-events', 'none')
    .text(d => d.owners.map(o => o.name).join('/').slice(0, 10))

  // ── Gateway node (center) ──
  const gwG = g.append('g').attr('class', 'gateway')

  gwG.append('circle')
    .attr('r', 36).attr('fill', '#5E5CE6').attr('opacity', 0.08)
    .attr('filter', 'url(#topo-glow)')
  gwG.append('circle')
    .attr('r', 28).attr('fill', '#1a1a2e')
    .attr('stroke', '#5E5CE6').attr('stroke-width', 2)
  gwG.append('circle')
    .attr('r', 34).attr('fill', 'none')
    .attr('stroke', '#5E5CE6').attr('stroke-width', 1).attr('opacity', 0.25)
  gwG.append('text')
    .attr('text-anchor', 'middle').attr('dominant-baseline', 'central')
    .attr('font-size', '20px').attr('pointer-events', 'none').text('🏠')
  gwG.append('text')
    .attr('y', 46).attr('text-anchor', 'middle')
    .attr('font-size', '11px').attr('fill', '#9898b8').attr('font-weight', 600)
    .attr('pointer-events', 'none').text('家庭网关')
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
function formatTime(v) {
  return v ? new Date(v).toLocaleString('zh-CN', { hour12: false }) : '—'
}

onMounted(loadTopology)
</script>

<template>
  <div class="topo-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h2 class="page-title">网络拓扑</h2>
        <span class="page-sub">
          在线 {{ stats.online }} / 共 {{ stats.total }} 台设备
        </span>
      </div>
      <el-button :loading="loading" :icon="Refresh" @click="loadTopology" size="small">
        刷新
      </el-button>
    </div>

    <!-- Canvas + Detail panel -->
    <div class="topo-body">
      <div class="canvas-wrap" v-loading="loading">
        <svg ref="svgEl" />

        <!-- Zoom controls -->
        <div class="zoom-controls">
          <button class="zoom-btn" @click="zoomIn">+</button>
          <button class="zoom-btn" @click="resetZoom" title="重置视角">⊙</button>
          <button class="zoom-btn" @click="zoomOut">−</button>
        </div>

        <!-- Legend -->
        <div class="legend">
          <div v-for="(cfg, key) in TYPE_CONFIG" :key="key" class="legend-item">
            <span class="legend-dot" :style="{ background: cfg.color }" />
            <span>{{ cfg.label }}</span>
          </div>
        </div>

        <!-- Empty state -->
        <div v-if="!loading && nodes.length === 0" class="empty-hint">
          暂无设备数据，请先在「设备列表」页面扫描网络
        </div>
      </div>

      <!-- Detail panel (slide in on node click) -->
      <transition name="panel-slide">
        <div v-if="selected" class="detail-panel">
          <div class="panel-head">
            <span
              class="type-badge"
              :style="{
                background: typeOf(selected).color + '20',
                color: typeOf(selected).color,
              }"
            >
              {{ typeOf(selected).icon }} {{ typeOf(selected).label }}
            </span>
            <button class="close-btn" @click="selected = null">✕</button>
          </div>

          <div class="panel-name">
            {{ selected.alias || selected.hostname || selected.ip || selected.mac }}
          </div>

          <div class="panel-status-row">
            <span class="status-dot" :class="selected.is_online ? 'online' : 'offline'" />
            <span class="status-text">{{ selected.is_online ? '在线' : '离线' }}</span>
            <span
              v-if="selected.is_online && selected.response_time_ms != null"
              class="latency"
              :style="{
                color: selected.response_time_ms < 5 ? '#26C281'
                  : selected.response_time_ms < 30 ? '#F2C94C'
                  : '#F07D38',
              }"
            >
              {{ Math.round(selected.response_time_ms) }}ms
            </span>
          </div>

          <div class="info-section">
            <div class="info-row"><span class="il">MAC</span><span class="iv mono">{{ selected.mac }}</span></div>
            <div class="info-row"><span class="il">IP</span><span class="iv mono">{{ selected.ip || '—' }}</span></div>
            <div class="info-row"><span class="il">主机名</span><span class="iv mono">{{ selected.hostname || '—' }}</span></div>
            <div class="info-row"><span class="il">厂商</span><span class="iv">{{ selected.vendor || '—' }}</span></div>
            <div class="info-row"><span class="il">最后在线</span><span class="iv">{{ formatTime(selected.last_seen) }}</span></div>
          </div>

          <div v-if="selected.owners?.length" class="info-section">
            <div class="section-title">归属成员</div>
            <div v-for="owner in selected.owners" :key="owner.id" class="owner-row">
              <span class="owner-dot" :class="owner.is_home ? 'home' : 'away'" />
              <span class="owner-name">{{ owner.name }}</span>
              <span class="owner-tag">{{ owner.is_home ? '在家' : '外出' }}</span>
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
  gap: 10px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--color-text-secondary);
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
.panel-slide-leave-active {
  transition: all 0.2s ease;
}
.panel-slide-enter-from,
.panel-slide-leave-to {
  opacity: 0;
  transform: translateX(20px);
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
.status-dot.online  { background: var(--color-online); box-shadow: 0 0 5px rgba(38, 194, 129, 0.5); }
.status-dot.offline { background: var(--color-offline); }
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

.owner-row {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 7px;
}
.owner-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.owner-dot.home { background: var(--color-online); }
.owner-dot.away { background: var(--color-offline); }
.owner-name {
  font-size: 13px;
  color: var(--color-text-primary);
  font-weight: 500;
}
.owner-tag {
  margin-left: auto;
  font-size: 11px;
  color: var(--color-text-muted);
}
</style>
