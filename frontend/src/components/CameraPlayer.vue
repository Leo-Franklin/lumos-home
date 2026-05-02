<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { Warning } from '@element-plus/icons-vue'
import videojs from 'video.js'
import 'video.js/dist/video-js.css'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  src: { type: String, required: true },
  mode: { type: String, default: 'recorded' }, // 'recorded' | 'live' | 'hls'
})

const error = ref('')
const loading = ref(true)
const hlsRef = ref(null)
let vjsPlayer = null

function onError(e) {
  loading.value = false
  if (props.mode === 'live') {
    error.value = t('cameras.streamLoadFailed')
    return
  }
  const code = e.target?.error?.code
  const msgs = {
    1: t('cameras.errAborted'),
    2: t('cameras.errNetwork'),
    3: t('cameras.errDecode'),
    4: t('cameras.errFormat'),
  }
  error.value = msgs[code] || t('cameras.errGeneric', { code })
}

function initVjs(src) {
  if (!hlsRef.value || !src) return
  if (vjsPlayer) {
    vjsPlayer.src({ src, type: 'application/x-mpegURL' })
    vjsPlayer.play().catch(() => {})
    loading.value = false
    return
  }
  vjsPlayer = videojs(hlsRef.value, {
    autoplay: 'muted',
    muted: true,
    controls: true,
    fluid: true,
    sources: [{ src, type: 'application/x-mpegURL' }],
    html5: { vhs: { overrideNative: true } },
  })
  vjsPlayer.on('ready', () => { loading.value = false })
  vjsPlayer.on('error', () => {
    error.value = t('cameras.hlsLoadFailed')
    loading.value = false
  })
}

watch(() => props.src, (src) => {
  error.value = ''
  loading.value = true
  if (props.mode === 'hls') nextTick(() => initVjs(src))
})

onMounted(() => {
  if (props.mode === 'hls') nextTick(() => initVjs(props.src))
})

onUnmounted(() => {
  if (vjsPlayer) { vjsPlayer.dispose(); vjsPlayer = null }
})
</script>

<template>
  <div style="position: relative; background: #000; border-radius: 4px; overflow: hidden;">
    <!-- HLS 播放：video.js -->
    <div v-if="mode === 'hls'">
      <video ref="hlsRef" class="video-js vjs-default-skin" style="width: 100%; max-height: 480px;" />
    </div>
    <!-- 实时预览：MJPEG img -->
    <img
      v-else-if="mode === 'live'"
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
      v-if="loading && !error && mode !== 'hls'"
      style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 14px;"
    >
      {{ mode === 'live' ? $t('common.connecting') : $t('common.loading') }}
    </div>
    <div
      v-if="error"
      style="position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #f56c6c; padding: 20px; text-align: center;"
    >
      <el-icon :size="40" style="margin-bottom: 12px;"><Warning /></el-icon>
      <span>{{ error }}</span>
      <el-link v-if="mode === 'recorded'" :href="src" target="_blank" style="margin-top: 12px; color: #409eff; font-size: 12px;">{{ $t('cameras.openInNewTab') }}</el-link>
    </div>
  </div>
</template>
