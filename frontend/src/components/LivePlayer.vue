<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getLiveInfo } from '@/api/cameras'
import { pickLiveMode, pickMjpegUrl, wsUrlFromApiPath } from '@/utils/livePlayer'
import { Go2RtcPlayer } from '@/lib/Go2RtcPlayer'

const props = defineProps({
  mac: { type: String, required: true },
})

const { t } = useI18n()
const loading = ref(true)
const error = ref('')
const mode = ref('')
const mjpegUrl = ref('')
const useMjpeg = ref(false)
const videoRef = ref(null)
let player = null

async function start() {
  loading.value = true
  error.value = ''
  mode.value = ''
  useMjpeg.value = false
  mjpegUrl.value = ''
  player?.stop()
  player = null

  const token = localStorage.getItem('token') || ''
  try {
    const { data } = await getLiveInfo(props.mac)
    const liveMode = pickLiveMode(data)
    if (liveMode === 'mse' && videoRef.value) {
      player = new Go2RtcPlayer(videoRef.value, wsUrlFromApiPath(data.mse_ws_url, token), {
        onMode: (m) => {
          mode.value = m
        },
        onError: (msg) => {
          error.value = msg
          useMjpeg.value = true
          mjpegUrl.value = pickMjpegUrl(data, token)
        },
      })
      player.start()
    } else {
      useMjpeg.value = true
      mjpegUrl.value = pickMjpegUrl(data, token)
      mode.value = 'MJPEG'
    }
  } catch {
    error.value = t('cameras.streamLoadFailed')
  } finally {
    loading.value = false
  }
}

onMounted(() => start())
onUnmounted(() => player?.stop())

watch(
  () => props.mac,
  () => start(),
)
</script>

<template>
  <div class="live-player">
    <div v-if="mode" class="live-player__badge">{{ mode }}</div>
    <video
      v-show="!useMjpeg"
      ref="videoRef"
      class="live-player__video"
      playsinline
      muted
      controls
    />
    <img
      v-if="useMjpeg && mjpegUrl"
      :src="mjpegUrl"
      class="live-player__video"
      @error="error = $t('cameras.streamLoadFailed')"
    />
    <div v-if="loading" class="live-player__overlay">{{ $t('common.connecting') }}</div>
    <div v-else-if="error" class="live-player__overlay live-player__overlay--error">
      {{ error }}
    </div>
  </div>
</template>

<style scoped>
.live-player {
  position: relative;
  background: #000;
  border-radius: var(--radius-sm, 4px);
  overflow: hidden;
  min-height: 240px;
}

.live-player__video {
  width: 100%;
  max-height: 480px;
  display: block;
  object-fit: contain;
}

.live-player__badge {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
  padding: 2px 8px;
  border-radius: var(--radius-sm, 4px);
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  font-size: 11px;
  letter-spacing: 0.04em;
  pointer-events: none;
}

.live-player__overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  background: rgba(0, 0, 0, 0.35);
}

.live-player__overlay--error {
  color: var(--color-error);
  padding: 16px;
  text-align: center;
}
</style>
