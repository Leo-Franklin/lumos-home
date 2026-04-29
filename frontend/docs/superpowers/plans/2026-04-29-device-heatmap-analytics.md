# Device Heatmap Enhancement & Analytics Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract and enhance the device activity heatmap into a reusable component, then build a full AnalyticsView with 8 D3-powered charts covering device health, network trends, and recording stats.

**Architecture:** Component-first — build `src/components/charts/` library first (BaseChart + 5 chart types), wire them into `AnalyticsView.vue`, refactor DevicesView to use the new component, and add 3 mini-sparklines to the Dashboard.

**Tech Stack:** Vue 3 Composition API (`<script setup>`), D3.js v7, Element Plus, Axios (baseURL `/api/v1`). Icons globally registered via `ElementPlusIconsVue` in `main.js`. Global CSS in `src/style.css`.

---

### Task 1: Analytics API module + chart color constants

**Files:**
- Create: `src/api/analytics.js`
- Create: `src/components/charts/chartColors.js`

- [ ] **Step 1: Create the analytics API module**

```js
// src/api/analytics.js
import api from './index'

export const getOnlineTrend     = (params) => api.get('/analytics/online-trend',        { params })
export const getDeviceTypeStats = ()        => api.get('/analytics/device-type-stats')
export const getResponseTime    = ()        => api.get('/analytics/response-time')
export const getRecordingCalendar = (params) => api.get('/analytics/recording-calendar', { params })
export const getNewDevices      = (params) => api.get('/analytics/new-devices',          { params })
export const getDeviceStability = (params) => api.get('/analytics/device-stability',     { params })
export const getTypeActivity    = (params) => api.get('/analytics/type-activity',        { params })
```

**Expected API response shapes (for backend implementation reference):**

```
GET /analytics/online-trend?range=7d
→ { data: [{ timestamp: "2026-04-22T00:00:00", count: 12 }, ...] }

GET /analytics/device-type-stats
→ { data: [{ type: "camera", count: 4 }, { type: "computer", count: 2 }, ...] }

GET /analytics/response-time
→ { data: [{ mac: "aa:bb:cc", name: "Camera-01", avg_ms: 12.5 }, ...] }
   (sorted by avg_ms ascending; max 20 entries)

GET /analytics/recording-calendar?range=90d
→ { data: [{ date: "2026-04-29", count: 5, duration_seconds: 3600 }, ...] }

GET /analytics/new-devices?range=90d&group_by=week
→ { data: [{ period: "2026-W17", count: 3 }, ...] }

GET /analytics/device-stability?range=7d
→ { data: [{ mac: "aa:bb:cc", name: "Camera-01", uptime_pct: 98.2 }, ...] }
   (sorted by uptime_pct descending; max 20 entries)

GET /analytics/type-activity?range=7d
→ { data: [{ hour: 0, camera: 2, computer: 1, phone: 0, iot: 3, unknown: 0 }, ...] }
   (24 entries, one per hour 0-23)

GET /devices/heatmap?range=7d&device_type=camera,phone   (existing endpoint, new response format)
→ { cells: [{ day: 0, hour: 0, count: 5, devices: ["Camera-01", "Camera-02"] }, ...] }
   (day: 0=Sun … 6=Sat; cells only for non-zero slots is fine)
```

- [ ] **Step 2: Create shared chart color constants**

```js
// src/components/charts/chartColors.js
export const DEVICE_TYPE_COLORS = {
  camera:   '#5E5CE6',
  computer: '#26C281',
  phone:    '#F2C94C',
  iot:      '#F07D38',
  unknown:  '#8B8B96',
}

export const DEVICE_TYPE_LABELS = {
  camera:   '摄像头',
  computer: '电脑',
  phone:    '手机',
  iot:      'IoT',
  unknown:  '未知',
}
```

- [ ] **Step 3: Commit**

```bash
git add src/api/analytics.js src/components/charts/chartColors.js
git commit -m "feat: add analytics API module and chart color constants"
```

---

### Task 2: BaseChart component

**Files:**
- Create: `src/components/charts/BaseChart.vue`

- [ ] **Step 1: Create BaseChart.vue**

```vue
<!-- src/components/charts/BaseChart.vue -->
<script setup>
defineProps({
  title:   String,
  loading: { type: Boolean, default: false },
  empty:   { type: Boolean, default: false },
  range:   { type: String, default: null },
  // [{ label: '近7天', value: '7d' }, ...]  — renders range selector in header when provided
  ranges:  { type: Array, default: null },
})
const emit = defineEmits(['range-change'])
</script>

<template>
  <div class="chart-card">
    <div class="chart-header">
      <span class="chart-title">{{ title }}</span>
      <el-radio-group
        v-if="ranges"
        :model-value="range"
        size="small"
        @change="emit('range-change', $event)"
      >
        <el-radio-button v-for="r in ranges" :key="r.value" :value="r.value">
          {{ r.label }}
        </el-radio-button>
      </el-radio-group>
    </div>
    <div class="chart-body">
      <el-skeleton v-if="loading" :rows="3" animated />
      <div v-else-if="empty" class="chart-empty">暂无数据</div>
      <slot v-else />
    </div>
  </div>
</template>

<style scoped>
.chart-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 20px;
}
.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  min-height: 28px;
}
.chart-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 160px;
  color: var(--color-text-muted);
  font-size: 13px;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add src/components/charts/BaseChart.vue
git commit -m "feat: add BaseChart wrapper component"
```

---

### Task 3: HeatmapChart component

**Files:**
- Create: `src/components/charts/HeatmapChart.vue`
- Modify: `src/style.css`

Enhanced extraction of the heatmap from `DevicesView.vue:74-146`. Uses purple color scale, device-type filter chips, and a custom floating tooltip.

- [ ] **Step 1: Add tooltip global style to src/style.css**

Open `src/style.css` and append:

```css
.chart-tooltip {
  background: var(--color-surface, #1e1e20);
  border: 1px solid var(--color-border, #333);
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--color-text-primary, #fff);
  line-height: 1.6;
  max-width: 220px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
}
```

- [ ] **Step 2: Create HeatmapChart.vue**

```vue
<!-- src/components/charts/HeatmapChart.vue -->
<script setup>
import { ref, watch, onMounted } from 'vue'
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
onMounted(renderChart)
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

    <div class="hm-scroll" :style="{ height: height + 'px' }">
      <div ref="svgRef" />
    </div>

    <div
      ref="tooltipRef"
      class="chart-tooltip"
      style="display:none;position:fixed;z-index:9999;pointer-events:none"
    />
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
```

- [ ] **Step 3: Verify manually**

Run `npm run dev`. Navigate to `/devices` (heatmap still lives there for now — Task 4 refactors it). The component file itself can't render standalone yet; verify no import errors in the browser console.

- [ ] **Step 4: Commit**

```bash
git add src/components/charts/HeatmapChart.vue src/style.css
git commit -m "feat: add HeatmapChart component with type filters and tooltip"
```

---

### Task 4: Refactor DevicesView to use HeatmapChart

**Files:**
- Modify: `src/views/DevicesView.vue`

Remove the inline D3 heatmap code (lines 74–146) and replace with the new component. The dialog wrapper stays in DevicesView.

- [ ] **Step 1: Replace the heatmap script section in DevicesView.vue**

Delete lines 74–146 (the entire `// ── Heatmap (C4) ──` block including all variables and functions: `heatmapDialog`, `heatmapRange`, `heatmapData`, `heatmapLoading`, `heatmapRef`, `DAYS`, `openHeatmap`, `fetchHeatmap`, `renderHeatmap`).

Add these imports at the top of `<script setup>` (alongside existing imports):

```js
import HeatmapChart from '@/components/charts/HeatmapChart.vue'
```

Replace the deleted block with:

```js
// ── Heatmap ──────────────────────────────────────────
const heatmapDialog  = ref(false)
const heatmapRange   = ref('7d')
const heatmapTypes   = ref([])
const heatmapData    = ref([])
const heatmapLoading = ref(false)

async function openHeatmap() {
  heatmapData.value  = []
  heatmapDialog.value = true
  await fetchHeatmap()
}

async function fetchHeatmap() {
  heatmapLoading.value = true
  try {
    const params = { range: heatmapRange.value }
    if (heatmapTypes.value.length) params.device_type = heatmapTypes.value.join(',')
    const { data } = await getDeviceHeatmap(params)
    heatmapData.value = data.cells ?? []
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '热力图加载失败')
  } finally {
    heatmapLoading.value = false
  }
}
```

- [ ] **Step 2: Replace the heatmap dialog in the template**

Find the dialog comment `<!-- 热力图 (C4) -->` (around line 264 in the original) and replace the entire `<el-dialog>` block with:

```vue
<!-- 热力图 -->
<el-dialog v-model="heatmapDialog" title="设备活跃热力图" width="760px" destroy-on-close>
  <el-skeleton v-if="heatmapLoading" :rows="4" animated />
  <HeatmapChart
    v-else
    :data="heatmapData"
    :range="heatmapRange"
    :device-types="heatmapTypes"
    :height="220"
    @range-change="(r) => { heatmapRange = r; fetchHeatmap() }"
    @type-filter-change="(t) => { heatmapTypes = t; fetchHeatmap() }"
  />
</el-dialog>
```

- [ ] **Step 3: Remove the unused D3 import**

Delete `import * as d3 from 'd3'` from the top of `<script setup>` (D3 is now encapsulated inside HeatmapChart).

- [ ] **Step 4: Verify manually**

Run `npm run dev`. Navigate to `/devices`, click "活跃热力图". Confirm:
- [ ] Dialog opens and shows loading skeleton
- [ ] Range buttons (今日/近7天/近30天) appear
- [ ] Device type filter chips appear
- [ ] Purple heatmap renders
- [ ] Hovering a cell shows tooltip with device names
- [ ] No console errors

- [ ] **Step 5: Commit**

```bash
git add src/views/DevicesView.vue
git commit -m "refactor: extract inline heatmap from DevicesView into HeatmapChart component"
```

---

### Task 5: LineChart component

**Files:**
- Create: `src/components/charts/LineChart.vue`

Responsive D3 area/line chart. Used for chart ③ and Dashboard sparkline.

- [ ] **Step 1: Create LineChart.vue**

```vue
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
  const x = d3.scaleTime().domain(d3.extent(xVals)).range([0, w])
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

watch(() => [props.data, props.height], renderChart, { deep: true })
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
```

- [ ] **Step 2: Commit**

```bash
git add src/components/charts/LineChart.vue
git commit -m "feat: add LineChart component (area/sparkline)"
```

---

### Task 6: BarChart component

**Files:**
- Create: `src/components/charts/BarChart.vue`

Three modes: `vertical` (chart ⑥), `horizontal` (charts ④ ⑦), `grouped` (chart ⑧).

- [ ] **Step 1: Create BarChart.vue**

```vue
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
```

- [ ] **Step 2: Commit**

```bash
git add src/components/charts/BarChart.vue
git commit -m "feat: add BarChart component (vertical/horizontal/grouped modes)"
```

---

### Task 7: DonutChart component

**Files:**
- Create: `src/components/charts/DonutChart.vue`

Used for chart ②. Shows device type distribution with interactive slices and a legend.

- [ ] **Step 1: Create DonutChart.vue**

```vue
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

watch(() => props.data, renderChart, { deep: true })
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
```

- [ ] **Step 2: Commit**

```bash
git add src/components/charts/DonutChart.vue
git commit -m "feat: add DonutChart component"
```

---

### Task 8: CalendarHeatmap component

**Files:**
- Create: `src/components/charts/CalendarHeatmap.vue`

GitHub contribution-style grid. Each cell = one day, color intensity = recording count.

- [ ] **Step 1: Create CalendarHeatmap.vue**

```vue
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
```

- [ ] **Step 2: Commit**

```bash
git add src/components/charts/CalendarHeatmap.vue
git commit -m "feat: add CalendarHeatmap component"
```

---

### Task 9: AnalyticsView page

**Files:**
- Create: `src/views/AnalyticsView.vue`

Assembles all 8 charts with independent loading states and the info-flow layout.

- [ ] **Step 1: Create AnalyticsView.vue**

```vue
<!-- src/views/AnalyticsView.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import BaseChart       from '@/components/charts/BaseChart.vue'
import HeatmapChart    from '@/components/charts/HeatmapChart.vue'
import LineChart       from '@/components/charts/LineChart.vue'
import BarChart        from '@/components/charts/BarChart.vue'
import DonutChart      from '@/components/charts/DonutChart.vue'
import CalendarHeatmap from '@/components/charts/CalendarHeatmap.vue'
import { DEVICE_TYPE_COLORS, DEVICE_TYPE_LABELS } from '@/components/charts/chartColors'
import {
  getOnlineTrend, getDeviceTypeStats, getResponseTime,
  getRecordingCalendar, getNewDevices, getDeviceStability, getTypeActivity,
} from '@/api/analytics'
import { getDeviceHeatmap } from '@/api/devices'

// ── ① Heatmap ──────────────────────────────────────────
const hmData    = ref([])
const hmRange   = ref('7d')
const hmTypes   = ref([])
const hmLoading = ref(false)

async function fetchHeatmap() {
  hmLoading.value = true
  try {
    const params = { range: hmRange.value }
    if (hmTypes.value.length) params.device_type = hmTypes.value.join(',')
    const { data } = await getDeviceHeatmap(params)
    hmData.value = data.cells ?? []
  } catch { ElMessage.error('热力图加载失败') }
  finally { hmLoading.value = false }
}

// ── ③ Online trend ──────────────────────────────────────
const trendData    = ref([])
const trendRange   = ref('7d')
const trendLoading = ref(false)

async function fetchTrend() {
  trendLoading.value = true
  try {
    const { data } = await getOnlineTrend({ range: trendRange.value })
    trendData.value = (data.data || []).map((d) => ({ x: new Date(d.timestamp), y: d.count }))
  } catch { ElMessage.error('在线趋势加载失败') }
  finally { trendLoading.value = false }
}

// ── ② Device type ───────────────────────────────────────
const typeData    = ref([])
const typeLoading = ref(false)

async function fetchTypeStats() {
  typeLoading.value = true
  try {
    const { data } = await getDeviceTypeStats()
    typeData.value = (data.data || []).map((d) => ({
      label: DEVICE_TYPE_LABELS[d.type] || d.type,
      value: d.count,
      color: DEVICE_TYPE_COLORS[d.type] || '#8B8B96',
    }))
  } catch { ElMessage.error('设备类型加载失败') }
  finally { typeLoading.value = false }
}

// ── ④ Response time ─────────────────────────────────────
const rtData    = ref([])
const rtLoading = ref(false)

async function fetchResponseTime() {
  rtLoading.value = true
  try {
    const { data } = await getResponseTime()
    rtData.value = (data.data || []).map((d) => ({
      label:      d.name || d.mac,
      value:      d.avg_ms,
      valueLabel: `${Math.round(d.avg_ms)}ms`,
    }))
  } catch { ElMessage.error('响应时延加载失败') }
  finally { rtLoading.value = false }
}

// ── ⑤ Recording calendar ────────────────────────────────
const calData    = ref([])
const calLoading = ref(false)

async function fetchCalendar() {
  calLoading.value = true
  try {
    const { data } = await getRecordingCalendar({ range: '90d' })
    calData.value = data.data || []
  } catch { ElMessage.error('录像日历加载失败') }
  finally { calLoading.value = false }
}

// ── ⑥ New devices ───────────────────────────────────────
const newDevData    = ref([])
const newDevLoading = ref(false)

async function fetchNewDevices() {
  newDevLoading.value = true
  try {
    const { data } = await getNewDevices({ range: '90d', group_by: 'week' })
    const items = data.data || []
    // Anomaly: count > 2× avg of previous 4 weeks → orange bar
    const prev4Avg = items.length >= 5
      ? items.slice(-5, -1).reduce((s, d) => s + d.count, 0) / 4
      : Infinity
    newDevData.value = items.map((d) => ({
      label: d.period,
      value: d.count,
      color: d.count > prev4Avg * 2 ? '#F07D38' : '#5E5CE6',
    }))
  } catch { ElMessage.error('新设备趋势加载失败') }
  finally { newDevLoading.value = false }
}

// ── ⑦ Stability ─────────────────────────────────────────
const stabilityData    = ref([])
const stabilityRange   = ref('7d')
const stabilityLoading = ref(false)

function stabilityColor(pct) {
  if (pct >= 90) return '#26C281'
  if (pct >= 70) return '#F2C94C'
  return '#F07D38'
}

async function fetchStability() {
  stabilityLoading.value = true
  try {
    const { data } = await getDeviceStability({ range: stabilityRange.value })
    stabilityData.value = (data.data || []).map((d) => ({
      label:      d.name || d.mac,
      value:      d.uptime_pct,
      valueLabel: `${d.uptime_pct.toFixed(1)}%`,
      color:      stabilityColor(d.uptime_pct),
    }))
  } catch { ElMessage.error('稳定性加载失败') }
  finally { stabilityLoading.value = false }
}

// ── ⑧ Type activity ─────────────────────────────────────
const activityData    = ref([])
const activityLoading = ref(false)

const ACTIVITY_GROUPS = Object.entries(DEVICE_TYPE_COLORS).map(([key, color]) => ({
  key, color, label: DEVICE_TYPE_LABELS[key],
}))

async function fetchTypeActivity() {
  activityLoading.value = true
  try {
    const { data } = await getTypeActivity({ range: '7d' })
    activityData.value = (data.data || []).map((d) => ({ label: String(d.hour), ...d }))
  } catch { ElMessage.error('类型活跃加载失败') }
  finally { activityLoading.value = false }
}

async function fetchAll() {
  await Promise.all([
    fetchHeatmap(), fetchTrend(), fetchTypeStats(), fetchResponseTime(),
    fetchCalendar(), fetchNewDevices(), fetchStability(), fetchTypeActivity(),
  ])
}

onMounted(fetchAll)
</script>

<template>
  <div>
    <div class="page-header">
      <div>
        <h2 class="page-title">数据分析</h2>
        <span class="page-sub">家庭网络综合洞察</span>
      </div>
      <el-button :icon="Refresh" @click="fetchAll">刷新全部</el-button>
    </div>

    <!-- ① 热力图 全宽 -->
    <BaseChart
      title="设备活跃时段"
      :loading="hmLoading"
      :empty="!hmLoading && !hmData.length"
      style="margin-bottom:16px"
    >
      <HeatmapChart
        :data="hmData"
        :range="hmRange"
        :device-types="hmTypes"
        :height="200"
        @range-change="(r) => { hmRange = r; fetchHeatmap() }"
        @type-filter-change="(t) => { hmTypes = t; fetchHeatmap() }"
      />
    </BaseChart>

    <!-- Row 2: ③ 趋势 + ⑤ 日历 -->
    <div class="row-2 mb">
      <BaseChart
        title="在线设备数量趋势"
        :loading="trendLoading"
        :empty="!trendLoading && !trendData.length"
        :range="trendRange"
        :ranges="[{ label: '近7天', value: '7d' }, { label: '近30天', value: '30d' }]"
        @range-change="(r) => { trendRange = r; fetchTrend() }"
      >
        <LineChart :data="trendData" color="#5E5CE6" :height="160" />
      </BaseChart>

      <BaseChart
        title="录像活动日历"
        :loading="calLoading"
        :empty="!calLoading && !calData.length"
      >
        <CalendarHeatmap :data="calData" :height="130" />
      </BaseChart>
    </div>

    <!-- Row 3: ② 类型分布 + ⑥ 新设备 + ⑧ 类型对比 -->
    <div class="row-3 mb">
      <BaseChart title="设备类型分布" :loading="typeLoading" :empty="!typeLoading && !typeData.length">
        <DonutChart :data="typeData" :size="160" />
      </BaseChart>

      <BaseChart title="新设备发现趋势" :loading="newDevLoading" :empty="!newDevLoading && !newDevData.length">
        <BarChart :data="newDevData" mode="vertical" :height="180" />
      </BaseChart>

      <BaseChart title="各类型活跃时段对比" :loading="activityLoading" :empty="!activityLoading && !activityData.length">
        <BarChart :data="activityData" mode="grouped" :groups="ACTIVITY_GROUPS" :height="180" />
      </BaseChart>
    </div>

    <!-- Row 4: ④ 时延 + ⑦ 稳定性 -->
    <div class="row-2">
      <BaseChart
        title="设备响应时延"
        :loading="rtLoading"
        :empty="!rtLoading && !rtData.length"
      >
        <BarChart
          :data="rtData"
          mode="horizontal"
          :height="220"
          :color-fn="(v) => v < 50 ? '#26C281' : v < 200 ? '#F2C94C' : '#F07D38'"
        />
      </BaseChart>

      <BaseChart
        title="设备在线稳定性"
        :loading="stabilityLoading"
        :empty="!stabilityLoading && !stabilityData.length"
        :range="stabilityRange"
        :ranges="[{ label: '近7天', value: '7d' }, { label: '近30天', value: '30d' }]"
        @range-change="(r) => { stabilityRange = r; fetchStability() }"
      >
        <BarChart :data="stabilityData" mode="horizontal" :height="220" />
      </BaseChart>
    </div>
  </div>
</template>

<style scoped>
.mb { margin-bottom: 16px; }
.row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.row-3 { display: grid; grid-template-columns: 1fr 1fr 2fr; gap: 16px; }
</style>
```

- [ ] **Step 2: Verify the page compiles**

Run `npm run dev`. Navigate to a URL that doesn't exist yet (we add the route in Task 10). Check the terminal for any compilation errors. Fix any import path issues before committing.

- [ ] **Step 3: Commit**

```bash
git add src/views/AnalyticsView.vue
git commit -m "feat: add AnalyticsView with 8 D3 charts"
```

---

### Task 10: Router + navigation

**Files:**
- Modify: `src/router/index.js`
- Modify: `src/layout/MainLayout.vue`

- [ ] **Step 1: Add analytics route to router/index.js**

In `src/router/index.js`, inside the `children` array, add after the `devices` route (line 13):

```js
{ path: 'analytics', component: () => import('@/views/AnalyticsView.vue') },
```

- [ ] **Step 2: Add sidebar link to MainLayout.vue**

In `src/layout/MainLayout.vue`, after the "设备列表" `<RouterLink>` block (around line 57), add:

```vue
<RouterLink to="/analytics" class="nav-item" :class="{ active: $route.path === '/analytics' }">
  <el-icon :size="16"><TrendCharts /></el-icon><span>数据分析</span>
</RouterLink>
```

`TrendCharts` is auto-registered in `main.js` via `ElementPlusIconsVue` — no import needed.

- [ ] **Step 3: Verify manually**

Run `npm run dev`:
- [ ] "数据分析" link appears in the sidebar between "设备列表" and "网络拓扑"
- [ ] Clicking navigates to `/analytics`
- [ ] Page renders with 8 chart card areas (loading skeletons while APIs are pending)
- [ ] No console errors

- [ ] **Step 4: Commit**

```bash
git add src/router/index.js src/layout/MainLayout.vue
git commit -m "feat: add /analytics route and sidebar navigation link"
```

---

### Task 11: Dashboard mini-charts

**Files:**
- Modify: `src/views/DashboardView.vue`

Add 3 mini-charts below the stats grid: 24h online sparkline, device type donut, recent new-device bars.

- [ ] **Step 1: Add imports to DashboardView.vue**

After `import { Refresh } from '@element-plus/icons-vue'`, add:

```js
import LineChart  from '@/components/charts/LineChart.vue'
import BarChart   from '@/components/charts/BarChart.vue'
import DonutChart from '@/components/charts/DonutChart.vue'
import { DEVICE_TYPE_COLORS, DEVICE_TYPE_LABELS } from '@/components/charts/chartColors'
import { getOnlineTrend, getDeviceTypeStats, getNewDevices } from '@/api/analytics'
```

- [ ] **Step 2: Add mini-chart data refs and fetch function**

After `const error = ref('')`, add:

```js
const sparkData  = ref([])
const donutData  = ref([])
const weekBarData = ref([])

async function fetchMiniCharts() {
  try {
    const [trend, types, newDev] = await Promise.all([
      getOnlineTrend({ range: '7d' }),
      getDeviceTypeStats(),
      getNewDevices({ range: '90d', group_by: 'week' }),
    ])
    sparkData.value = (trend.data.data || [])
      .map((d) => ({ x: new Date(d.timestamp), y: d.count }))
    donutData.value = (types.data.data || []).map((d) => ({
      label: DEVICE_TYPE_LABELS[d.type] || d.type,
      value: d.count,
      color: DEVICE_TYPE_COLORS[d.type] || '#8B8B96',
    }))
    weekBarData.value = (newDev.data.data || []).slice(-7).map((d) => ({
      label: d.period.slice(-2),
      value: d.count,
    }))
  } catch { /* mini charts are non-critical */ }
}
```

- [ ] **Step 3: Call fetchMiniCharts in onMounted**

Find the existing `onMounted` block and add one line:

```js
onMounted(() => {
  fetchDashboard()
  fetchMiniCharts()          // ← add this
  timer = setInterval(fetchDashboard, 30000)
})
```

- [ ] **Step 4: Add mini-charts template**

Inside `<template v-if="data">`, after the closing `</div>` of `.stats-grid`, add:

```vue
<div v-if="sparkData.length || donutData.length" class="mini-charts">
  <div class="mini-card">
    <div class="mini-label">24H 在线趋势</div>
    <LineChart :data="sparkData" color="#5E5CE6" :height="60" :mini="true" />
  </div>
  <div class="mini-card">
    <div class="mini-label">设备类型</div>
    <DonutChart :data="donutData" :size="80" :mini="true" />
  </div>
  <div class="mini-card">
    <div class="mini-label">近期新设备</div>
    <BarChart :data="weekBarData" mode="vertical" :height="60" :mini="true" />
  </div>
</div>
```

- [ ] **Step 5: Add styles to DashboardView.vue `<style scoped>`**

```css
.mini-charts {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-top: 16px;
}
.mini-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 14px 16px;
}
.mini-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 10px;
}
```

- [ ] **Step 6: Verify manually**

Run `npm run dev`, navigate to `/dashboard`. Confirm:
- [ ] Mini-chart row appears below stat cards once data loads
- [ ] Sparkline shows a line
- [ ] Donut shows a ring
- [ ] Bar chart shows bars
- [ ] No layout breakage in existing stat cards

- [ ] **Step 7: Commit**

```bash
git add src/views/DashboardView.vue
git commit -m "feat: add mini sparkline charts to Dashboard"
```
