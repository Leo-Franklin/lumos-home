<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { User, Lock, ArrowDown } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { useLocaleStore } from '@/stores/locale'

const { t, locale } = useI18n()
const localeStore = useLocaleStore()

const langOptions = [
  { label: '中文', value: 'zh-CN' },
  { label: 'English', value: 'en' },
]

function switchLang(lang) {
  localeStore.setLocale(lang)
}
const router = useRouter()
const auth = useAuthStore()

const form = ref({ username: 'admin', password: '' })
const loading = ref(false)

async function handleLogin() {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning(t('login.fillRequired'))
    return
  }
  loading.value = true
  try {
    await auth.login(form.value.username, form.value.password)
    router.push('/devices')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('login.loginFailed'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="lang-bar">
      <el-dropdown @command="switchLang">
        <span class="lang-trigger">
          {{ locale === 'zh-CN' ? '中文' : 'English' }}
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
    <div class="login-box">
      <div class="login-logo">
        <div class="logo-icon-wrap">
          <el-icon :size="22" class="logo-icon"><House /></el-icon>
        </div>
        <h2 class="logo-title">{{ $t('login.brandTitle') }}</h2>
        <p class="logo-sub">{{ $t('login.subtitle') }}</p>
      </div>
      <div class="login-divider" />
      <el-form @submit.prevent="handleLogin" :model="form" label-width="0">
        <el-form-item>
          <el-input
            v-model="form.username"
            :placeholder="$t('login.username')"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            :placeholder="$t('login.password')"
            type="password"
            size="large"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          :loading="loading"
          style="width: 100%; height: 40px; font-size: 14px"
          @click="handleLogin"
        >
          {{ $t('login.submit') }}
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: var(--color-bg);
  background-image: radial-gradient(circle, rgba(255, 255, 255, 0.035) 1px, transparent 1px);
  background-size: 28px 28px;
}

.lang-bar {
  width: 380px;
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
  transition: background var(--duration-fast) ease-out,
              color var(--duration-fast) ease-out;
}
.lang-trigger:hover {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
}

.login-box {
  width: 380px;
  padding: 36px 40px 40px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  position: relative;
  overflow: hidden;
}
.login-box::before {
  content: '';
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 60%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(94, 92, 230, 0.55), transparent);
}

.login-logo {
  text-align: center;
  margin-bottom: 24px;
}
.logo-icon-wrap {
  width: 50px;
  height: 50px;
  background: rgba(94, 92, 230, 0.1);
  border: 1px solid rgba(94, 92, 230, 0.22);
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 14px;
  box-shadow: 0 0 18px rgba(94, 92, 230, 0.14);
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

.login-divider {
  height: 1px;
  background: var(--color-border-subtle);
  margin: 0 0 24px;
}
</style>
