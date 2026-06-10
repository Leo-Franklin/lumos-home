<script setup>
import { useI18n } from 'vue-i18n'
import EmptyState from '@/components/EmptyState.vue'
import { useRecordingParams } from '@/composables/useRecordingParams'

const props = defineProps({
  presets: { type: Array, required: true },
  /** 'select' for dropdown (schedule), 'cards' for clickable cards (manual record) */
  mode: { type: String, default: 'select' },
  clearable: { type: Boolean, default: true },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  hint: { type: String, default: '' },
  showCardsHint: { type: Boolean, default: true },
})

const model = defineModel({ type: [String, null], default: null })

const { t } = useI18n()
const { formatResolution } = useRecordingParams()

function togglePreset(id) {
  if (props.mode !== 'cards') return
  model.value = model.value === id ? null : id
}
</script>

<template>
  <template v-if="mode === 'select'">
    <p v-if="hint" class="picker-hint">{{ hint }}</p>
    <el-select
      v-model="model"
      :placeholder="placeholder || t('recording.selectPreset')"
      style="width: 100%"
      :clearable="clearable"
      :disabled="disabled"
    >
      <el-option v-for="p in presets" :key="p.id" :label="p.name" :value="p.id" />
    </el-select>
    <p v-if="!disabled && !presets.length" class="picker-empty">
      {{ t('recording.noPresetsAvailable') }}
    </p>
  </template>

  <template v-else>
    <template v-if="presets.length">
      <p v-if="mode === 'cards' && showCardsHint" class="picker-hint">
        {{ t('recording.selectPresetOptional') }}
      </p>
      <div class="picker-cards">
        <el-card
          v-for="p in presets"
          :key="p.id"
          shadow="hover"
          :class="['picker-card', { 'picker-card--selected': model === p.id }]"
          @click="togglePreset(p.id)"
        >
          <div class="picker-card__name">{{ p.name }}</div>
          <div class="picker-card__meta">
            {{ formatResolution(p.resolution) }} &middot; {{ p.segment_duration }}s &middot;
            {{ p.bitrate }}k
          </div>
          <div class="picker-card__fps">{{ p.fps }} fps</div>
        </el-card>
      </div>
    </template>
    <EmptyState v-else :title="t('recording.noPresetsAvailable')" size="small" />
  </template>
</template>

<style scoped>
.picker-hint,
.picker-empty {
  margin: 0 0 var(--space-3);
  color: var(--color-text-muted);
  font-size: 13px;
}

.picker-empty {
  margin-top: var(--space-2);
  margin-bottom: 0;
}

.picker-cards {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-5);
}

.picker-card {
  width: 130px;
  cursor: pointer;
  transition: all var(--duration-fast) var(--easing-standard);
  border: 1px solid var(--color-border-subtle);
}

.picker-card:hover {
  border-color: var(--color-primary);
}

.picker-card--selected {
  border-color: var(--color-primary);
  background: var(--color-primary-subtle);
}

.picker-card__name {
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 4px;
}

.picker-card__meta,
.picker-card__fps {
  font-size: 11px;
  color: var(--color-text-muted);
}

.picker-card__fps {
  margin-top: 2px;
}
</style>
