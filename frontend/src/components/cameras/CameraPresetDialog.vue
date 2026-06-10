<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Edit, Delete, Star, StarFilled, Plus } from '@element-plus/icons-vue'
import EmptyState from '@/components/EmptyState.vue'
import RecordingParamFields from '@/components/recording/RecordingParamFields.vue'
import { useRecordingParams } from '@/composables/useRecordingParams'

const props = defineProps({
  camera: { type: Object, default: null },
  list: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
  editing: { type: [Number, null], default: null },
})
const emit = defineEmits(['add', 'edit', 'save', 'delete', 'setDefault'])

const visible = defineModel({ type: Boolean, required: true })
const form = defineModel('form', { type: Object, required: true })

const { t } = useI18n()
const { formatResolution } = useRecordingParams()

const title = computed(() =>
  props.camera
    ? t('cameras.managePresetsTitle', { host: props.camera.onvif_host })
    : t('cameras.managePresets'),
)

const formTitle = computed(() => (props.editing ? t('cameras.editPreset') : t('cameras.addPreset')))
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="title"
    width="860px"
    class="preset-dialog-wrap"
    body-class="dialog-body--split"
    :destroy-on-close="true"
  >
    <div v-loading="loading" class="preset-dialog">
      <section class="preset-dialog__list">
        <div class="preset-dialog__list-header">
          <span class="preset-dialog__list-title">
            {{ t('cameras.existingPresets') }}
            <span v-if="list.length" class="preset-dialog__count">{{ list.length }}</span>
          </span>
          <el-button size="small" :icon="Plus" @click="emit('add')">
            {{ t('cameras.addPreset') }}
          </el-button>
        </div>

        <el-scrollbar v-if="list.length" class="preset-dialog__scroll">
          <div
            v-for="preset in list"
            :key="preset.id"
            :class="['preset-row', { 'preset-row--editing': editing === preset.id }]"
            @click="emit('edit', preset)"
          >
            <div class="preset-row__main">
              <div class="preset-row__name">
                <el-icon v-if="preset.is_default" class="preset-row__star" aria-hidden="true">
                  <StarFilled />
                </el-icon>
                <span>{{ preset.name }}</span>
              </div>
              <div class="preset-row__meta">
                {{ formatResolution(preset.resolution) }}
                <span class="preset-row__sep">&middot;</span>
                {{ preset.segment_duration }}s
                <span class="preset-row__sep">&middot;</span>
                {{ preset.bitrate }} kbps
                <span class="preset-row__sep">&middot;</span>
                {{ preset.fps }} fps
              </div>
            </div>
            <div class="preset-row__actions" @click.stop>
              <el-tooltip :content="t('common.edit')" :show-after="400">
                <el-button
                  size="small"
                  :icon="Edit"
                  :aria-label="t('common.edit')"
                  @click="emit('edit', preset)"
                />
              </el-tooltip>
              <el-tooltip :content="t('cameras.setDefault')" :show-after="400">
                <el-button
                  size="small"
                  :icon="Star"
                  :disabled="preset.is_default"
                  :aria-label="t('cameras.setDefault')"
                  @click="emit('setDefault', preset)"
                />
              </el-tooltip>
              <el-tooltip :content="t('cameras.delete')" :show-after="400">
                <el-button
                  size="small"
                  type="danger"
                  :icon="Delete"
                  :aria-label="t('cameras.delete')"
                  @click="emit('delete', preset)"
                />
              </el-tooltip>
            </div>
          </div>
        </el-scrollbar>
        <EmptyState v-else :title="t('cameras.noPresets')" size="small" />
      </section>

      <section class="preset-dialog__form-panel">
        <el-scrollbar class="preset-dialog__form-scroll">
          <h4 class="preset-dialog__form-title">{{ formTitle }}</h4>
          <RecordingParamFields v-model="form" :show-templates="!editing" />
        </el-scrollbar>
      </section>
    </div>

    <template #footer>
      <div class="preset-dialog__footer">
        <el-button v-if="editing" @click="emit('add')">{{ t('common.cancel') }}</el-button>
        <el-button @click="visible = false">{{ t('common.close') }}</el-button>
        <el-button type="primary" :loading="saving" @click="emit('save')">
          {{ editing ? t('common.save') : t('common.add') }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.preset-dialog {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: var(--space-5);
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.preset-dialog__list {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.preset-dialog__list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.preset-dialog__list-title {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.preset-dialog__count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 var(--space-1);
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: var(--color-surface-raised);
}

.preset-dialog__scroll {
  flex: 1;
  min-height: 0;
  height: 0;
}

.preset-dialog__scroll :deep(.el-scrollbar__wrap) {
  max-height: 100%;
}

.preset-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3);
  margin-bottom: var(--space-2);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  cursor: pointer;
  transition:
    border-color var(--duration-fast) var(--easing-standard),
    background var(--duration-fast) var(--easing-standard);
}

.preset-row:last-child {
  margin-bottom: 0;
}

.preset-row:hover {
  border-color: var(--color-border);
  background: var(--color-surface-raised);
}

.preset-row--editing {
  border-color: var(--color-primary);
  background: var(--color-primary-subtle);
}

.preset-row__main {
  min-width: 0;
  flex: 1;
}

.preset-row__name {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 2px;
}

.preset-row__star {
  color: var(--color-primary);
  font-size: 14px;
  flex-shrink: 0;
}

.preset-row__meta {
  font-size: 11px;
  color: var(--color-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.preset-row__sep {
  margin: 0 4px;
}

.preset-row__actions {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  flex-shrink: 0;
}

.preset-dialog__form-panel {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised);
  min-height: 0;
  overflow: hidden;
}

.preset-dialog__form-scroll {
  height: 100%;
}

.preset-dialog__form-scroll :deep(.el-scrollbar__view) {
  padding: var(--space-4);
}

.preset-dialog__form-title {
  margin: 0 0 var(--space-3);
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.preset-dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
