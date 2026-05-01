<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '0 2 * * *' },
})
const emit = defineEmits(['update:modelValue'])

const activeTab = ref('preset')
const customTime = ref('02:00')
const customDays = ref([1, 2, 3, 4, 5, 6, 0])

const PRESETS = [
  { label: '每天凌晨 2:00',   cron: '0 2 * * *' },
  { label: '工作日早 8:00',   cron: '0 8 * * 1-5' },
  { label: '每天晚上 22:00',  cron: '0 22 * * *' },
  { label: '每 30 分钟',      cron: '*/30 * * * *' },
  { label: '周末凌晨',        cron: '0 0 * * 6,0' },
  { label: '每小时整点',      cron: '0 * * * *' },
]

const DAYS = [
  { label: '一', value: 1 },
  { label: '二', value: 2 },
  { label: '三', value: 3 },
  { label: '四', value: 4 },
  { label: '五', value: 5 },
  { label: '六', value: 6 },
  { label: '日', value: 0 },
]

const TABS = [
  { key: 'preset',   label: '快速选择' },
  { key: 'custom',   label: '自定义时间' },
  { key: 'advanced', label: '高级 (Cron)' },
]

function buildCustomCron() {
  if (!customTime.value) return `0 2 * * *`
  const [hStr, mStr] = customTime.value.split(':')
  const h = parseInt(hStr, 10)
  const m = parseInt(mStr, 10)
  if (customDays.value.length === 0 || customDays.value.length === 7)
    return `${m} ${h} * * *`
  const sorted = [...customDays.value].sort((a, b) => a - b)
  return `${m} ${h} * * ${sorted.join(',')}`
}

function toggleDay(val) {
  const idx = customDays.value.indexOf(val)
  customDays.value = idx === -1
    ? [...customDays.value, val]
    : customDays.value.filter((d) => d !== val)
  if (activeTab.value === 'custom') emit('update:modelValue', buildCustomCron())
}

function onTimeChange() {
  if (activeTab.value === 'custom') emit('update:modelValue', buildCustomCron())
}

function selectPreset(cron) {
  emit('update:modelValue', cron)
}

function onAdvancedInput(val) {
  emit('update:modelValue', val)
}

function switchTab(tab) {
  if (activeTab.value === tab) return
  activeTab.value = tab
  if (tab === 'custom') emit('update:modelValue', buildCustomCron())
}

function cronDescription(cron) {
  if (!cron) return '未设置'
  const preset = PRESETS.find((p) => p.cron === cron)
  if (preset) return preset.label + ' 触发'
  const parts = cron.trim().split(/\s+/)
  if (parts.length !== 5) return `自定义：${cron}`
  const [min, hour, , , dow] = parts
  if (min === '*' && hour === '*') return '每分钟触发'
  if (min.startsWith('*/')) return `每 ${min.slice(2)} 分钟触发`
  if (hour === '*') return `每小时第 ${min} 分触发`
  const timeStr = `${String(hour).padStart(2, '0')}:${String(min).padStart(2, '0')}`
  if (dow === '*') return `每天 ${timeStr} 触发`
  if (dow === '1-5') return `工作日 ${timeStr} 触发`
  if (dow === '6,0' || dow === '0,6') return `周末 ${timeStr} 触发`
  return `自定义：${cron}`
}

const description = computed(() => cronDescription(props.modelValue))
const CRON_RE = /^(\*|[0-9,\-*/]+)\s+(\*|[0-9,\-*/]+)\s+(\*|[0-9,\-*/]+)\s+(\*|[0-9,\-*/]+)\s+(\*|[0-9,\-*/]+)$/
const valid = computed(() => CRON_RE.test(props.modelValue?.trim() ?? ''))
</script>

<template>
  <div class="cron-selector">
    <div class="tab-bar">
      <button
        v-for="tab in TABS"
        :key="tab.key"
        class="tab-btn"
        :class="{ active: activeTab === tab.key }"
        @click="switchTab(tab.key)"
      >{{ tab.label }}</button>
    </div>

    <div v-if="activeTab === 'preset'" class="preset-grid">
      <div
        v-for="p in PRESETS"
        :key="p.cron"
        class="preset-card"
        :class="{ selected: modelValue === p.cron }"
        @click="selectPreset(p.cron)"
      >
        <div class="preset-label">{{ p.label }}</div>
        <div class="preset-cron">{{ p.cron }}</div>
      </div>
    </div>

    <div v-else-if="activeTab === 'custom'" class="custom-panel">
      <div class="custom-row">
        <div class="custom-field">
          <div class="field-label">触发时间</div>
          <el-time-picker
            v-model="customTime"
            format="HH:mm"
            value-format="HH:mm"
            :clearable="false"
            style="width: 130px"
            @change="onTimeChange"
          />
        </div>
      </div>
      <div class="day-section">
        <div class="field-label">星期（全选 = 每天）</div>
        <div class="day-buttons">
          <button
            v-for="d in DAYS"
            :key="d.value"
            class="day-btn"
            :class="{ active: customDays.includes(d.value) }"
            @click="toggleDay(d.value)"
          >{{ d.label }}</button>
        </div>
      </div>
    </div>

    <div v-else class="advanced-panel">
      <el-input
        :model-value="modelValue"
        placeholder="分 时 日 月 周，如 0 2 * * *"
        @input="onAdvancedInput"
      />
      <div class="adv-hint">格式：分 小时 日 月 周几（5 字段）</div>
    </div>

    <div class="preview-bar" :class="valid ? 'valid' : 'invalid'">
      <span class="preview-icon">{{ valid ? '✓' : '✗' }}</span>
      <span class="preview-text">
        {{ description }}
        <span class="preview-cron">（{{ modelValue }}）</span>
      </span>
    </div>
  </div>
</template>

<style scoped>
.cron-selector {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tab-bar {
  display: flex;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
}

.tab-btn {
  flex: 1;
  padding: 8px 4px;
  background: transparent;
  border: none;
  border-right: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-size: 13px;
  cursor: pointer;
  font-family: var(--font-sans);
  transition: background 0.15s, color 0.15s;
}
.tab-btn:last-child { border-right: none; }
.tab-btn.active { background: var(--color-primary); color: #fff; }
.tab-btn:not(.active):hover {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
}

.preset-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.preset-card {
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 10px 12px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.preset-card:hover { border-color: var(--color-primary); }
.preset-card.selected {
  background: rgba(94, 92, 230, 0.08);
  border-color: var(--color-primary);
}

.preset-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.preset-cron {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 2px;
  font-family: var(--font-mono);
}
.preset-card.selected .preset-cron { color: var(--color-primary); }

.custom-panel { display: flex; flex-direction: column; gap: 14px; }
.custom-row { display: flex; gap: 12px; }
.custom-field { display: flex; flex-direction: column; gap: 4px; }

.field-label {
  font-size: 11px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.day-section { display: flex; flex-direction: column; gap: 6px; }
.day-buttons { display: flex; gap: 6px; }

.day-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--color-border);
  background: var(--color-surface-raised);
  color: var(--color-text-muted);
  font-size: 12px;
  cursor: pointer;
  font-family: var(--font-sans);
  transition: background 0.15s, color 0.15s, border-color 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}
.day-btn.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}

.advanced-panel { display: flex; flex-direction: column; gap: 4px; }
.adv-hint { font-size: 11px; color: var(--color-text-muted); }

.preview-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid;
  font-size: 13px;
}
.preview-bar.valid {
  background: rgba(38, 194, 129, 0.06);
  border-color: rgba(38, 194, 129, 0.2);
}
.preview-bar.invalid {
  background: rgba(240, 82, 82, 0.06);
  border-color: rgba(240, 82, 82, 0.2);
}

.preview-icon { flex-shrink: 0; }
.preview-bar.valid  .preview-icon { color: var(--color-online, #26C281); }
.preview-bar.invalid .preview-icon { color: var(--color-error, #F05252); }

.preview-bar.valid  .preview-text { color: var(--color-online, #26C281); }
.preview-bar.invalid .preview-text { color: var(--color-error, #F05252); }

.preview-cron {
  opacity: 0.6;
  font-size: 11px;
  font-family: var(--font-mono);
}
</style>
