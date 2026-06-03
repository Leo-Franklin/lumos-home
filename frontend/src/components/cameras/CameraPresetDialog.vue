<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Edit, Delete, Star, StarFilled } from '@element-plus/icons-vue'
import EmptyState from '@/components/EmptyState.vue'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  camera: { type: Object, default: null },
  list: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
  form: { type: Object, required: true },
  editing: { type: [Number, null], default: null },
})
const emit = defineEmits([
  'update:modelValue',
  'add',
  'edit',
  'save',
  'delete',
  'setDefault',
])

const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const title = computed(() =>
  props.camera
    ? t('cameras.managePresetsTitle', { host: props.camera.onvif_host })
    : t('cameras.managePresets'),
)
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="title"
    width="900px"
    :destroy-on-close="true"
  >
    <div v-loading="loading" style="padding-right: 8px">
      <!-- Preset list -->
      <div v-if="list.length" style="margin-bottom: 16px">
        <el-table :data="list" size="small" border>
          <el-table-column prop="name" :label="t('cameras.presetName')" width="120" />
          <el-table-column prop="resolution" :label="t('cameras.resolution')" width="100" />
          <el-table-column prop="segment_duration" :label="t('cameras.segmentSec')" width="90" />
          <el-table-column prop="bitrate" :label="t('cameras.bitrateKbps')" width="100" />
          <el-table-column prop="fps" :label="t('cameras.fps')" width="60" />
          <el-table-column :label="t('cameras.isDefault')" width="70" align="center">
            <template #default="{ row }">
              <el-icon v-if="row.is_default" color="var(--color-primary)"><StarFilled /></el-icon>
            </template>
          </el-table-column>
          <el-table-column :label="t('cameras.actions')" width="280" align="center">
            <template #default="{ row }">
              <div class="preset-action-group">
                <el-button size="small" :icon="Edit" @click="emit('edit', row)">
                  {{ t('common.edit') }}
                </el-button>
                <el-button
                  size="small"
                  :icon="Star"
                  :disabled="row.is_default"
                  @click="emit('setDefault', row)"
                >
                  {{ t('cameras.setDefault') }}
                </el-button>
                <el-button size="small" type="danger" :icon="Delete" @click="emit('delete', row)" />
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <EmptyState
        v-else
        :title="t('cameras.noPresets')"
        size="small"
      />

      <!-- Add/Edit form -->
      <el-divider />
      <h4 style="margin: 0 0 12px">
        {{ editing ? t('cameras.editPreset') : t('cameras.addPreset') }}
      </h4>
      <el-form :model="form" label-width="140px" style="max-width: 640px">
        <el-form-item :label="t('cameras.presetName')">
          <el-input
            v-model="form.name"
            :placeholder="t('cameras.presetNamePlaceholder')"
            style="width: 160px"
          />
        </el-form-item>
        <el-form-item :label="t('cameras.resolution')">
          <el-select v-model="form.resolution" style="width: 140px">
            <el-option value="1920x1080" :label="t('cameras.res1920x1080')" />
            <el-option value="1280x720" :label="t('cameras.res1280x720')" />
            <el-option value="640x360" :label="t('cameras.res640x360')" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('cameras.segmentSec')">
          <el-input-number v-model="form.segment_duration" :min="60" :max="3600" style="width: 140px" />
        </el-form-item>
        <el-form-item :label="t('cameras.bitrateKbps')">
          <el-input-number v-model="form.bitrate" :min="256" :max="20000" :step="256" style="width: 140px" />
        </el-form-item>
        <el-form-item :label="t('cameras.frameRate')">
          <el-input-number v-model="form.fps" :min="5" :max="60" style="width: 140px" />
        </el-form-item>
      </el-form>
    </div>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.close') }}</el-button>
      <el-button type="primary" :loading="saving" @click="emit('save')">
        {{ editing ? t('common.save') : t('common.add') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.preset-action-group {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  flex-wrap: nowrap;
  white-space: nowrap;
}

.preset-action-group :deep(.el-button) {
  flex-shrink: 0;
}
</style>
