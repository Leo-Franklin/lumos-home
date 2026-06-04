<script setup>
import { useRouter } from 'vue-router'
import { House, Position } from '@element-plus/icons-vue'

const router = useRouter()

function goHome() {
  const token = localStorage.getItem('token')
  router.push(token ? '/dashboard' : '/login')
}
</script>

<template>
  <div class="notfound-page">
    <div class="notfound-box">
      <div class="notfound-illu">
        <span class="digit four">4</span>
        <div class="orbit">
          <el-icon :size="56" class="orbit-icon"><Position /></el-icon>
        </div>
        <span class="digit four">4</span>
      </div>
      <h1 class="notfound-title">{{ $t('common.notFound.title') }}</h1>
      <p class="notfound-desc">{{ $t('common.notFound.desc') }}</p>
      <el-button
        type="primary"
        size="large"
        :icon="House"
        class="back-btn"
        @click="goHome"
      >
        {{ $t('common.notFound.backHome') }}
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.notfound-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: var(--color-bg);
  background-image: radial-gradient(circle, rgba(255, 255, 255, 0.035) 1px, transparent 1px);
  background-size: 28px 28px;
  padding: 24px;
}

.notfound-box {
  width: 420px;
  max-width: 100%;
  padding: 48px 40px 44px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  position: relative;
  overflow: hidden;
  text-align: center;
  animation: fade-up var(--duration-slow) var(--easing-snap) both;
}

.notfound-box::before {
  content: '';
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 60%;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-primary), transparent);
}

.notfound-illu {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin: 4px 0 28px;
  font-family: var(--font-display);
  font-size: 140px;
  line-height: 1;
  font-weight: 700;
  letter-spacing: -0.06em;
}

.digit {
  background: linear-gradient(180deg, var(--color-primary) 0%, var(--color-primary-hover) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 0 40px var(--color-primary-subtle);
  filter: drop-shadow(0 0 12px rgba(99, 102, 241, 0.35));
}

.orbit {
  width: 120px;
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1.5px dashed var(--color-primary-border);
  border-radius: 50%;
  background: var(--color-primary-subtle);
  box-shadow: 0 0 28px var(--color-primary-subtle);
  animation: orbit-spin 16s linear infinite;
}

.orbit-icon {
  color: var(--color-primary);
  filter: drop-shadow(0 0 6px var(--color-primary-border));
}

@keyframes orbit-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

.notfound-title {
  margin: 0 0 8px;
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.03em;
}

.notfound-desc {
  margin: 0 0 28px;
  font-size: 13px;
  color: var(--color-text-muted);
  line-height: 1.6;
}

.back-btn {
  width: 100%;
  height: 40px;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.01em;
}
</style>
