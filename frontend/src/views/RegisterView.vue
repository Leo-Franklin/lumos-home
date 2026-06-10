<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { User, Lock, ArrowDown } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { useLocaleStore } from '@/stores/locale'
import { useApiError } from '@/composables/useApiError'

const { t, locale } = useI18n()
const handleError = useApiError()
const localeStore = useLocaleStore()

const langOptions = [
  { label: t('login.langChinese'), value: 'zh-CN' },
  { label: t('login.langEnglish'), value: 'en' },
]

function switchLang(lang) {
  localeStore.setLocale(lang)
}
const router = useRouter()
const auth = useAuthStore()

const form = ref({ email: '', password: '', confirmPassword: '' })
const formRef = ref(null)
const loading = ref(false)

const rules = {
  email: [
    { required: true, message: t('login.emailRequired'), trigger: 'blur' },
    { type: 'email', message: t('login.emailInvalid'), trigger: ['blur', 'change'] },
  ],
  password: [
    { required: true, message: t('login.passwordRequired'), trigger: 'blur' },
    { min: 8, message: t('login.passwordTooShort'), trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: t('login.confirmPasswordRequired'), trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== form.value.password) {
          callback(new Error(t('login.passwordMismatch')))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

async function handleRegister() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    await auth.register(form.value.email, form.value.password)
    ElMessage.success(t('login.registerSuccess'))
    router.push('/login')
  } catch (e) {
    handleError(e, 'login.registerFailed')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-page">
    <div class="lang-bar">
      <el-dropdown @command="switchLang">
        <span class="lang-trigger">
          {{ locale === 'zh-CN' ? $t('login.langChinese') : $t('login.langEnglish') }}
          <el-icon :size="12" style="margin-left: 4px"><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              v-for="opt in langOptions"
              :key="opt.value"
              :command="opt.value"
              :class="{ 'is-active': locale === opt.value }"
            >
              {{ opt.label }}
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
    <div class="register-box">
      <div class="register-logo">
        <div class="logo-icon-wrap">
          <el-icon :size="22" class="logo-icon"><House /></el-icon>
        </div>
        <h2 class="logo-title">{{ $t('login.registerTitle') }}</h2>
        <p class="logo-sub">{{ $t('login.subtitle') }}</p>
      </div>
      <div class="register-divider" />
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="0"
        :disabled="loading"
        @submit.prevent="handleRegister"
      >
        <el-form-item prop="email">
          <el-input
            v-model="form.email"
            :placeholder="$t('login.email')"
            type="email"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            :placeholder="$t('login.password')"
            type="password"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            :placeholder="$t('login.confirmPassword')"
            type="password"
            size="large"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleRegister"
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          :loading="loading"
          style="width: 100%; height: 40px; font-size: 14px"
          @click="handleRegister"
        >
          {{ $t('login.registerTitle') }}
        </el-button>
        <el-button
          text
          size="small"
          style="width: 100%; margin-top: 16px"
          :disabled="loading"
          @click="router.push('/login')"
        >
          {{ $t('login.goToLogin') }}
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.register-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: var(--space-6) var(--space-4);
  background: var(--color-bg);
  background-image: radial-gradient(circle, rgba(255, 255, 255, 0.035) 1px, transparent 1px);
  background-size: 28px 28px;
}

.lang-bar {
  width: 100%;
  max-width: 380px;
  display: flex;
  justify-content: flex-end;
  margin-bottom: 8px;
}
.lang-trigger {
  display: inline-flex;
  align-items: center;
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  transition:
    background var(--duration-fast) ease-out,
    color var(--duration-fast) ease-out;
}
.lang-trigger:hover {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
}

.register-box {
  width: 100%;
  max-width: 380px;
  padding: 32px 28px 36px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  position: relative;
  overflow: hidden;
}
.register-box::before {
  content: '';
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 60%;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-primary), transparent);
}

.register-logo {
  text-align: center;
  margin-bottom: 24px;
}
.logo-icon-wrap {
  width: 50px;
  height: 50px;
  background: var(--color-primary-subtle);
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 14px;
  box-shadow: 0 0 18px var(--color-primary-subtle);
}
.logo-icon {
  color: var(--color-primary);
}
.logo-title {
  margin: 0 0 4px;
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.03em;
}
.logo-sub {
  font-size: 12px;
  color: var(--color-text-muted);
  letter-spacing: 0.01em;
}

.register-divider {
  height: 1px;
  background: var(--color-border-subtle);
  margin: 0 0 24px;
}
</style>
