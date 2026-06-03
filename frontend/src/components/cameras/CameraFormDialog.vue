<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDevicesStore } from '@/stores/devices'
import { useDLNAStore } from '@/stores/dlna'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  mode: { type: String, default: 'add' }, // 'add' | 'edit'
  form: { type: Object, required: true },
  submitting: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'submit', 'cancel'])

const { t } = useI18n()
const devicesStore = useDevicesStore()
const dlnaStore = useDLNAStore()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const title = computed(() => (props.mode === 'add' ? t('cameras.addCamera') : t('cameras.editCamera')))
const isAdd = computed(() => props.mode === 'add')

function onSubmit() { emit('submit') }
function onCancel() { emit('cancel') }
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="title"
    :width="isAdd ? '480px' : '500px'"
    :close-on-press-escape="!submitting"
    @close="onCancel"
  >
    <el-form :model="form" :label-width="isAdd ? '110px' : '120px'">
      <!-- Add mode: device picker -->
      <el-form-item v-if="isAdd" :label="t('cameras.deviceMac')">
        <el-select
          v-model="form.device_mac"
          :placeholder="t('cameras.selectDevice')"
          filterable
          style="width: 100%"
        >
          <el-option
            v-for="d in devicesStore.items"
            :key="d.mac"
            :label="`${d.alias || d.hostname || d.mac} (${d.ip})`"
            :value="d.mac"
          />
        </el-select>
      </el-form-item>

      <el-form-item :label="t('cameras.onvifHost')">
        <el-input
          v-if="isAdd"
          v-model="form.onvif_host"
          :placeholder="t('cameras.onvifPlaceholder')"
        />
        <el-input v-else v-model="form.onvif_host" />
      </el-form-item>

      <el-form-item :label="t('cameras.onvifPort')">
        <el-input-number v-model="form.onvif_port" :min="1" :max="65535" />
      </el-form-item>

      <el-form-item :label="t('cameras.onvifUser')">
        <el-input v-model="form.onvif_user" />
      </el-form-item>

      <el-form-item :label="t('cameras.onvifPassword')">
        <el-input
          v-model="form.onvif_password"
          type="password"
          show-password
          :placeholder="isAdd ? '' : t('cameras.passwordPlaceholder')"
        />
      </el-form-item>

      <el-form-item :label="t('cameras.rtspPort')">
        <el-input-number v-model="form.rtsp_port" :min="1" :max="65535" />
      </el-form-item>

      <!-- Edit-only fields -->
      <template v-if="!isAdd">
        <el-form-item :label="t('cameras.rtspUrl')">
          <el-input v-model="form.rtsp_url" :placeholder="t('cameras.rtspUrlPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('cameras.streamProfile')">
          <el-select v-model="form.stream_profile" style="width: 100%">
            <el-option value="mainStream" :label="t('cameras.mainStream')" />
            <el-option value="subStream" :label="t('cameras.subStream')" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('cameras.dlnaAutoCast')">
          <el-select
            v-model="form.auto_cast_dlna"
            clearable
            :placeholder="t('cameras.dlnaPlaceholder')"
            style="width: 100%"
          >
            <el-option
              v-for="d in dlnaStore.devices"
              :key="d.udn"
              :label="d.friendly_name || d.udn"
              :value="d.udn"
            />
          </el-select>
        </el-form-item>
      </template>
    </el-form>

    <template #footer>
      <el-button :disabled="submitting" @click="onCancel">{{ t('cameras.cancel') }}</el-button>
      <el-button type="primary" :loading="submitting" @click="onSubmit">
        {{ isAdd ? t('cameras.add') : t('cameras.save') }}
      </el-button>
    </template>
  </el-dialog>
</template>
