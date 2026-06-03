<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  loading: { type: Boolean, default: false },
  result: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue'])

const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
</script>

<template>
  <el-dialog v-model="visible" :title="t('cameras.probeResult')" width="520px">
    <div v-if="loading" style="text-align: center; padding: 20px">
      <el-text>{{ t('cameras.probing') }}</el-text>
    </div>
    <template v-else-if="result">
      <el-descriptions :column="2" border>
        <el-descriptions-item
          v-for="(v, k) in result.device_info"
          :key="k"
          :label="k"
        >{{ v }}</el-descriptions-item>
      </el-descriptions>
      <h4 style="margin: 16px 0 8px">{{ t('cameras.availableStreams') }}</h4>
      <el-table :data="result.profiles" size="small" border>
        <el-table-column prop="index" label="#" width="50" />
        <el-table-column prop="name" :label="t('cameras.name')" />
        <el-table-column prop="token" :label="t('cameras.token')" />
        <el-table-column prop="rtsp_url" :label="t('cameras.rtspUrl')" show-overflow-tooltip />
      </el-table>
      <el-alert
        v-if="result.auto_set_rtsp_url"
        type="success"
        style="margin-top: 12px"
        :closable="false"
      >
        {{ t('cameras.rtspUrlWritten', { url: result.auto_set_rtsp_url }) }}
      </el-alert>
    </template>
  </el-dialog>
</template>
