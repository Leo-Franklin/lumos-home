import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listCameras } from '@/api/cameras'

export const useCamerasStore = defineStore('cameras', () => {
  const items = ref([])
  const loading = ref(false)

  async function fetchCameras() {
    loading.value = true
    try {
      const { data } = await listCameras()
      items.value = data
    } finally {
      loading.value = false
    }
  }

  function onRecordingStarted(mac) {
    const cam = items.value.find((c) => c.device_mac === mac)
    if (cam) cam.is_recording = true
  }

  function onRecordingStopped(mac) {
    const cam = items.value.find((c) => c.device_mac === mac)
    if (cam) cam.is_recording = false
  }

  function onCameraOffline(mac) {
    const cam = items.value.find((c) => c.device_mac === mac)
    if (cam) cam.is_online = false
  }

  function onCameraOnline(mac) {
    const cam = items.value.find((c) => c.device_mac === mac)
    if (cam) cam.is_online = true
  }

  return { items, loading, fetchCameras, onRecordingStarted, onRecordingStopped, onCameraOffline, onCameraOnline }
})
