<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { forgotPassword } from '@/api/auth'
import { useApiError } from '@/composables/useApiError'

const { t } = useI18n()
const handleError = useApiError()

const visible = defineModel({ type: Boolean, default: false })

const formRef = ref(null)
const form = ref({ email: '' })
const loading = ref(false)
const sent = ref(false)

const rules = {
  email: [
    { required: true, message: t('login.emailRequired'), trigger: 'blur' },
    { type: 'email', message: t('login.emailInvalid'), trigger: ['blur', 'change'] },
  ],
}

function close() {
  visible.value = false
  // reset on close so the next open is clean
  setTimeout(() => {
    form.value = { email: '' }
    sent.value = false
    formRef.value?.clearValidate()
  }, 200)
}

async function submit() {
  if (!formRef.value) return
  try { await formRef.value.validate() } catch { return }
  loading.value = true
  try {
    await forgotPassword(form.value.email)
    sent.value = true
    ElMessage.success(t('login.forgotPasswordSent'))
  } catch (e) {
    handleError(e, 'login.forgotPasswordFailed')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    :title="$t('login.forgotPasswordTitle')"
    width="420px"
    :close-on-click-modal="false"
    @update:model-value="(v) => v ? visible = true : close()"
    @close="close"
  >
    <p class="dialog-desc">{{ $t('login.forgotPasswordDesc') }}</p>
    <el-form
      v-if="!sent"
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="0"
      @submit.prevent="submit"
    >
      <el-form-item prop="email">
        <el-input
          v-model="form.email"
          :placeholder="$t('login.email')"
          size="large"
          type="email"
        />
      </el-form-item>
    </el-form>
    <div v-else class="sent-hint">
      <el-icon class="sent-icon"><CircleCheck /></el-icon>
      <p>{{ $t('login.forgotPasswordSent') }}</p>
    </div>
    <template #footer>
      <el-button @click="close">{{ $t('common.cancel') }}</el-button>
      <el-button v-if="!sent" type="primary" :loading="loading" @click="submit">
        {{ $t('common.submit') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.dialog-desc {
  font-size: 12px;
  color: var(--color-text-muted);
  margin: 0 0 16px;
  line-height: 1.5;
}
.sent-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 16px 0;
  color: var(--color-text-secondary);
  font-size: 13px;
  text-align: center;
}
.sent-icon {
  font-size: 36px;
  color: var(--color-online);
}
</style>
