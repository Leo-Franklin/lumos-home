<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const auth = useAuthStore()

const form = ref({ username: 'admin', password: '' })
const loading = ref(false)

async function handleLogin() {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.value.username, form.value.password)
    router.push('/devices')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-box">
      <div class="login-logo">
        <div class="logo-icon-wrap">
          <el-icon :size="22" class="logo-icon"><House /></el-icon>
        </div>
        <h2 class="logo-title">智能家居管理</h2>
        <p class="logo-sub">Smart Home Control Panel</p>
      </div>
      <div class="login-divider" />
      <el-form @submit.prevent="handleLogin" :model="form" label-width="0">
        <el-form-item>
          <el-input
            v-model="form.username"
            placeholder="用户名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            placeholder="密码"
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
          登录
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: var(--color-bg);
  background-image: radial-gradient(circle, rgba(255, 255, 255, 0.035) 1px, transparent 1px);
  background-size: 28px 28px;
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
