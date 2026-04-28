<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/index'
import { Refresh } from '@element-plus/icons-vue'

const health = ref(null)
const loading = ref(false)
const error = ref('')

function formatUptime(s) {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60)
  return `${h} 小时 ${m} 分钟`
}

async function fetchHealth() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/health')
    health.value = data
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(fetchHealth)
</script>

<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">系统设置</h2>
      <el-button :icon="Refresh" :loading="loading" @click="fetchHealth">刷新</el-button>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon class="mb" />

    <template v-if="health">
      <el-descriptions title="系统健康状态" :column="2" border>
        <el-descriptions-item label="整体状态">
          <el-tag :type="health.status === 'healthy' ? 'success' : 'danger'">{{ health.status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="版本">{{ health.version }}</el-descriptions-item>
        <el-descriptions-item label="运行时长">
          {{ formatUptime(health.uptime_seconds) }}
        </el-descriptions-item>
      </el-descriptions>

      <el-descriptions title="组件状态" :column="2" border style="margin-top: 20px">
        <el-descriptions-item v-for="(v, k) in health.checks" :key="k" :label="k">
          <el-tag v-if="typeof v === 'boolean'" :type="v ? 'success' : 'danger'" size="small">
            {{ v ? '正常' : '异常' }}
          </el-tag>
          <template v-else-if="typeof v === 'object'">
            在线 {{ v.online }} / 总计 {{ v.total }}
          </template>
          <span v-else>{{ v }}</span>
        </el-descriptions-item>
      </el-descriptions>
    </template>

    <el-skeleton v-else-if="loading" :rows="4" animated />
  </div>
</template>

<style scoped>
.mb { margin-bottom: 16px }
</style>
