<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  modelValue: { type: String, default: '0 2 * * *' },
})
const emit = defineEmits(['update:modelValue'])

const customTime = ref('02:00')
const customDays = ref([1, 2, 3, 4, 5, 6, 0])

watch(
  () => props.modelValue,
  (val) => {
    if (!val) return
    const parts = val.trim().split(/\s+/)
    if (parts.length !== 5) return
    const [m, h, , , dow] = parts
    if (!/^\d+$/.test(m) || !/^\d+$/.test(h)) return
    customTime.value = `${String(Number(h)).padStart(2, '0')}:${String(Number(m)).padStart(2, '0')}`
    if (dow === '*') {
      customDays.value = [0, 1, 2, 3, 4, 5, 6]
    } else {
      customDays.value = dow
        .split(',')
        .map(Number)
        .filter((n) => !isNaN(n))
    }
  },
  { immediate: true },
)

const PRESETS = [
  { labelKey: 'schedule.presetDaily2am', cron: '0 2 * * *' },
  { labelKey: 'schedule.presetWeekday8am', cron: '0 8 * * 1-5' },
  { labelKey: 'schedule.presetDaily10pm', cron: '0 22 * * *' },
  { labelKey: 'schedule.presetEvery30min', cron: '*/30 * * * *' },
  { labelKey: 'schedule.presetWeekendMidnight', cron: '0 0 * * 6,0' },
  { labelKey: 'schedule.presetHourly', cron: '0 * * * *' },
]

const activeTab = ref(PRESETS.some((p) => p.cron === props.modelValue) ? 'preset' : 'advanced')

const DAYS = [
  { labelKey: 'schedule.weekdayShort.1', value: 1 },
  { labelKey: 'schedule.weekdayShort.2', value: 2 },
  { labelKey: 'schedule.weekdayShort.3', value: 3 },
  { labelKey: 'schedule.weekdayShort.4', value: 4 },
  { labelKey: 'schedule.weekdayShort.5', value: 5 },
  { labelKey: 'schedule.weekdayShort.6', value: 6 },
  { labelKey: 'schedule.weekdayShort.0', value: 0 },
]

const TABS = [
  { key: 'preset', labelKey: 'schedule.tabPreset' },
  { key: 'custom', labelKey: 'schedule.tabCustom' },
  { key: 'advanced', labelKey: 'schedule.tabAdvanced' },
]

function buildCustomCron() {
  if (!customTime.value) return `0 2 * * *`
  const [hStr, mStr] = customTime.value.split(':')
  const h = parseInt(hStr, 10)
  const m = parseInt(mStr, 10)
  if (customDays.value.length === 0 || customDays.value.length === 7) return `${m} ${h} * * *`
  const sorted = [...customDays.value].sort((a, b) => a - b)
  return `${m} ${h} * * ${sorted.join(',')}`
}

function toggleDay(val) {
  const idx = customDays.value.indexOf(val)
  customDays.value =
    idx === -1 ? [...customDays.value, val] : customDays.value.filter((d) => d !== val)
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
  if (!cron) return t('schedule.cronNotSet')
  const preset = PRESETS.find((p) => p.cron === cron)
  if (preset) return t(preset.labelKey) + ' ' + t('schedule.trigger')
  const parts = cron.trim().split(/\s+/)
  if (parts.length !== 5) return t('schedule.cronCustom', { expr: cron })
  const [min, hour, , , dow] = parts
  if (min === '*' && hour === '*') return t('schedule.cronEveryMinute')
  if (min.startsWith('*/')) return t('schedule.cronEveryNMinute', { n: min.slice(2) })
  if (hour === '*') return t('schedule.cronHourlyAt', { min })
  const timeStr = `${String(hour).padStart(2, '0')}:${String(min).padStart(2, '0')}`
  if (dow === '*') return t('schedule.cronDaily', { time: timeStr })
  if (dow === '1-5') return t('schedule.cronWeekday', { time: timeStr })
  if (dow === '1,2,3,4,5') return t('schedule.cronWeekday', { time: timeStr })
  if (dow === '6,0' || dow === '0,6') return t('schedule.cronWeekend', { time: timeStr })
  return t('schedule.cronCustom', { expr: cron })
}

const description = computed(() => cronDescription(props.modelValue))
const CRON_RE =
  /^(\*|[0-9,\-*/]+)\s+(\*|[0-9,\-*/]+)\s+(\*|[0-9,\-*/]+)\s+(\*|[0-9,\-*/]+)\s+(\*|[0-9,\-*/]+)$/
const valid = computed(() => CRON_RE.test(props.modelValue?.trim() ?? ''))
const showPreview = computed(() => activeTab.value === 'advanced' || !valid.value)
</script>

<template>
  <div class="cron-selector">
    <div class="tab-bar" role="tablist">
      <button
        v-for="tab in TABS"
        :key="tab.key"
        type="button"
        class="tab-btn"
        :class="{ active: activeTab === tab.key }"
        role="tab"
        :aria-selected="activeTab === tab.key"
        @click="switchTab(tab.key)"
      >
        {{ $t(tab.labelKey) }}
      </button>
    </div>

    <div class="tab-panel">
      <div v-if="activeTab === 'preset'" class="preset-grid">
        <button
          v-for="p in PRESETS"
          :key="p.cron"
          type="button"
          class="preset-card"
          :class="{ selected: modelValue === p.cron }"
          @click="selectPreset(p.cron)"
        >
          <span class="preset-label">{{ $t(p.labelKey) }}</span>
          <span v-if="modelValue === p.cron" class="preset-check" aria-hidden="true">✓</span>
        </button>
      </div>

      <div v-else-if="activeTab === 'custom'" class="custom-panel">
        <div class="custom-row">
          <div class="custom-field">
            <div class="field-label">{{ $t('schedule.triggerTime') }}</div>
            <el-time-picker
              v-model="customTime"
              format="HH:mm"
              value-format="HH:mm"
              :clearable="false"
              style="width: 100%"
              @change="onTimeChange"
            />
          </div>
        </div>
        <div class="day-section">
          <div class="field-label">{{ $t('schedule.weekday') }}</div>
          <div class="day-buttons">
            <button
              v-for="d in DAYS"
              :key="d.value"
              type="button"
              class="day-btn"
              :class="{ active: customDays.includes(d.value) }"
              @click="toggleDay(d.value)"
            >
              {{ $t(d.labelKey) }}
            </button>
          </div>
        </div>
        <div class="custom-summary">{{ description }}</div>
      </div>

      <div v-else class="advanced-panel">
        <el-input
          :model-value="modelValue"
          :placeholder="$t('schedule.advPlaceholder')"
          @input="onAdvancedInput"
        />
        <div class="adv-hint">{{ $t('schedule.advHint') }}</div>
      </div>
    </div>

    <div v-if="showPreview" class="preview-bar" :class="valid ? 'valid' : 'invalid'">
      <span class="preview-icon">{{ valid ? '✓' : '✗' }}</span>
      <span class="preview-text">{{ description }}</span>
    </div>
  </div>
</template>

<style scoped>
.cron-selector {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  box-sizing: border-box;
}

.tab-bar {
  display: inline-flex;
  align-self: flex-start;
  gap: 4px;
  padding: 3px;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md, 8px);
}

.tab-btn {
  padding: 6px 12px;
  background: transparent;
  border: none;
  border-radius: calc(var(--radius-md, 8px) - 2px);
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  font-family: var(--font-sans);
  white-space: nowrap;
  transition:
    background var(--duration-fast, 0.15s),
    color var(--duration-fast, 0.15s);
}

.tab-btn.active {
  background: var(--color-primary);
  color: var(--color-text-inverse);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.12);
}

.tab-btn:not(.active):hover {
  color: var(--color-text-primary);
}

.tab-panel {
  min-height: 120px;
}

.preset-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.preset-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-sm, 6px);
  padding: 10px 12px;
  cursor: pointer;
  text-align: left;
  font-family: var(--font-sans);
  transition:
    border-color var(--duration-fast, 0.15s),
    background var(--duration-fast, 0.15s);
}

.preset-card:hover {
  border-color: var(--color-primary-border);
  background: var(--color-surface-overlay);
}

.preset-card.selected {
  background: var(--color-primary-subtle);
  border-color: var(--color-primary);
}

.preset-label {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-primary);
  line-height: 1.35;
}

.preset-check {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  color: var(--color-primary);
}

.custom-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.custom-row {
  display: flex;
  gap: 12px;
}

.custom-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-width: 180px;
}

.field-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.day-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.day-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.day-btn {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1px solid var(--color-border);
  background: var(--color-surface-raised);
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  font-family: var(--font-sans);
  transition:
    background var(--duration-fast, 0.15s),
    color var(--duration-fast, 0.15s),
    border-color var(--duration-fast, 0.15s);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.day-btn.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-text-inverse);
}

.custom-summary {
  font-size: 12px;
  color: var(--color-text-muted);
  padding: 8px 10px;
  background: var(--color-surface-raised);
  border-radius: var(--radius-sm, 6px);
  border: 1px solid var(--color-border-subtle);
}

.advanced-panel {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.adv-hint {
  font-size: 11px;
  color: var(--color-text-muted);
  line-height: 1.45;
}

.preview-bar {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-sm, 6px);
  border: 1px solid;
  font-size: 12px;
  line-height: 1.45;
}

.preview-bar.valid {
  background: rgba(16, 185, 129, 0.08);
  border-color: rgba(16, 185, 129, 0.25);
}

.preview-bar.invalid {
  background: rgba(239, 68, 68, 0.06);
  border-color: rgba(239, 68, 68, 0.2);
}

.preview-icon {
  flex-shrink: 0;
  font-weight: 700;
}

.preview-bar.valid .preview-icon,
.preview-bar.valid .preview-text {
  color: var(--color-online);
}

.preview-bar.invalid .preview-icon,
.preview-bar.invalid .preview-text {
  color: var(--color-error);
}
</style>
