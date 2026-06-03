<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Lock, House } from '@element-plus/icons-vue'
import { resetPassword } from '@/api/auth'
import { useApiError } from '@/composables/useApiError'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const handleError = useApiError()

const token = computed(() => route.query.token || '')
const form = ref({ password: '', confirm: '' })
const formRef = ref(null)
const loading = ref(false)

const rules = computed(() => ({
  password: [
    { required: true, message: t('login.passwordRequired'), trigger: 'blur' },
    { min: 8, message: t('login.passwordTooShort'), trigger: 'blur' },
  ],
  confirm: [
    { required: true, message: t('login.confirmPasswordRequired'), trigger: 'blur' },
    {
      validator: (_, value, cb) => {
        if (value !== form.value.password) cb(new Error(t('login.passwordMismatch')))
        else cb()
      },
      trigger: 'blur',
    },
  ],
}))

onMounted(() => {
  if (!token.value) {
    ElMessage.warning(t('login.resetPasswordInvalidLink'))
  }
})

async function submit() {
  if (!token.value) {
    ElMessage.error(t('login.resetPasswordInvalidLink'))
    return
  }
  if (!formRef.value) return
  try { await formRef.value.validate() } catch { return }
  loading.value = true
  try {
    await resetPassword(token.value, form.value.password)
    ElMessage.success(t('login.resetPasswordSuccess'))
    router.push('/login')
  } catch (e) {
    handleError(e, 'login.resetPasswordFailed')
  } finally {
    loading.value = false
  }
}

function goLogin() {
  router.push('/login')
}
</script>

<template>
  <div class="reset-page">
    <div class="reset-box">
      <h2 class="reset-title">{{ $t('login.resetPasswordTitle') }}</h2>
      <p v-if="!token" class="reset-desc warn">
        {{ $t('login.resetPasswordInvalidLink') }}
      </p>
      <p v-else class="reset-desc">{{ $t('login.forgotPasswordDesc') }}</p>
      <el-form
        v-if="token"
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="0"
        :disabled="loading"
        @submit.prevent="submit"
      >
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="$t('login.resetPasswordNew')"
            size="large"
            :prefix-icon="Lock"
          />
        </el-form-item>
        <el-form-item prop="confirm">
          <el-input
            v-model="form.confirm"
            type="password"
            show-password
            :placeholder="$t('login.confirmPassword')"
            size="large"
            :prefix-icon="Lock"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          :loading="loading"
          style="width: 100%; height: 40px; font-size: 14px"
          @click="submit"
        >
          {{ $t('login.resetPasswordSubmit') }}
        </el-button>
      </el-form>
      <el-button
        v-else
        type="primary"
        size="large"
        :icon="House"
        style="width: 100%; height: 40px; font-size: 14px"
        @click="goLogin"
      >
        {{ $t('common.back') }}
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.reset-page {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: var(--color-bg);
  background-image: radial-gradient(circle, rgba(255, 255, 255, 0.035) 1px, transparent 1px);
  background-size: 28px 28px;
}
.reset-box {
  width: 380px;
  padding: 36px 40px 40px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}
.reset-title {
  margin: 0 0 12px;
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text-primary);
  text-align: center;
  letter-spacing: -0.03em;
}
.reset-desc {
  font-size: 12px;
  color: var(--color-text-muted);
  margin: 0 0 24px;
  text-align: center;
  line-height: 1.5;
}
.reset-desc.warn {
  color: var(--color-error);
}
</style>
