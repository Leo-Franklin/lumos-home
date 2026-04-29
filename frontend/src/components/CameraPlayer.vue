<script setup>
import { ref, watch } from 'vue'
import { Warning } from '@element-plus/icons-vue'

const props = defineProps({
  src: { type: String, required: true },
  mode: { type: String, default: 'recorded' }, // 'recorded' | 'live'
})

const error = ref('')
const loading = ref(true)

watch(() => props.src, () => {
  error.value = ''
  loading.value = true
})

function onError(e) {
  loading.value = false
  if (props.mode === 'live') {
    error.value = '实时画面加载失败，请检查摄像头是否在线及 RTSP 地址是否正确'
    return
  }
  const code = e.target?.error?.code
  const msgs = {
    1: '加载被中止',
    2: '网络错误，无法加载视频',
    3: '视频解码失败（可能是不支持的编码格式，如 H.265）',
    4: '视频格式不支持或资源不可用',
  }
  error.value = msgs[code] || `视频加载失败（错误码 ${code}）`
}
</script>

<template>
  <div style="position: relative; background: #000; border-radius: 4px; overflow: hidden;">
    <!-- 实时预览：MJPEG img -->
    <img
      v-if="mode === 'live'"
      :src="src"
      style="width: 100%; max-height: 480px; display: block; object-fit: contain;"
      @load="loading = false"
      @error="onError"
    />
    <!-- 录像回放：video -->
    <video
      v-else
      :src="src"
      controls
      autoplay
      muted
      style="width: 100%; max-height: 480px; display: block;"
      @error="onError"
      @loadeddata="loading = false"
    />

    <div
      v-if="loading && !error"
      style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 14px;"
    >
      {{ mode === 'live' ? '连接摄像头中...' : '加载中...' }}
    </div>
    <div
      v-if="error"
      style="position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #f56c6c; padding: 20px; text-align: center;"
    >
      <el-icon :size="40" style="margin-bottom: 12px;"><Warning /></el-icon>
      <span>{{ error }}</span>
      <el-link v-if="mode !== 'live'" :href="src" target="_blank" style="margin-top: 12px; color: #409eff; font-size: 12px;">在新标签页中打开查看详情</el-link>
    </div>
  </div>
</template>
