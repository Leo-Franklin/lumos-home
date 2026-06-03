<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  title: { type: String, required: true },
  loading: { type: Boolean, default: false },
  width: { type: String, default: '480px' },
  confirmText: { type: String, default: '' },
  cancelText: { type: String, default: '' },
  confirmDisabled: { type: Boolean, default: false },
  closeOnClickModal: { type: Boolean, default: true },
  destroyOnClose: { type: Boolean, default: false },
  showFooter: { type: Boolean, default: true },
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

function onConfirm() {
  emit('confirm')
}

function onCancel() {
  emit('cancel')
  visible.value = false
}
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="title"
    :width="width"
    :close-on-click-modal="closeOnClickModal && !loading"
    :destroy-on-close="destroyOnClose"
    class="form-dialog"
  >
    <div v-loading="loading" class="form-dialog__body">
      <slot />
    </div>

    <template v-if="showFooter" #footer>
      <div class="form-dialog__footer">
        <slot name="footer">
          <el-button :disabled="loading" @click="onCancel">
            {{ cancelText || $t ? $t('common.cancel') : 'Cancel' }}
          </el-button>
          <el-button
            type="primary"
            :loading="loading"
            :disabled="confirmDisabled"
            @click="onConfirm"
          >
            {{ confirmText || $t ? $t('common.save') : 'Save' }}
          </el-button>
        </slot>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.form-dialog__body {
  min-height: 40px;
}

.form-dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
