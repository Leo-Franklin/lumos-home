import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listCameras,
  listPresets,
  createPreset,
  deletePreset,
  setDefaultPreset,
  getCamera,
} from '@/api/cameras'

export const useCamerasStore = defineStore('cameras', () => {
  const items = ref([])
  const loading = ref(false)
  const presets = ref({}) // { mac: [preset1, preset2] }
  const defaultPresetId = ref({}) // { mac: presetId }

  async function fetchCameras() {
    loading.value = true
    try {
      const { data } = await listCameras()
      items.value = data
    } finally {
      loading.value = false
    }
  }

  async function loadPresets(mac) {
    try {
      const [presetsRes, camRes] = await Promise.all([listPresets(mac), getCamera(mac)])
      presets.value[mac] = presetsRes.data || []
      defaultPresetId.value[mac] = camRes.data.default_preset_id
    } catch (e) {
      if (e.response?.status === 404) {
        try {
          const presetsRes = await listPresets(mac)
          presets.value[mac] = presetsRes.data || []
          delete defaultPresetId.value[mac]
        } catch (presetsErr) {
          if (presetsErr.response?.status === 404) {
            presets.value[mac] = []
            delete defaultPresetId.value[mac]
          } else {
            throw presetsErr
          }
        }
      } else {
        throw e
      }
    }
  }

  async function addPreset(mac, data) {
    const res = await createPreset(mac, data)
    await loadPresets(mac)
    return res.data
  }

  async function removePreset(mac, presetId) {
    await deletePreset(mac, presetId)
    await loadPresets(mac)
  }

  async function setDefault(mac, presetId) {
    await setDefaultPreset(mac, presetId)
    defaultPresetId.value[mac] = presetId
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

  return {
    items,
    loading,
    presets,
    defaultPresetId,
    fetchCameras,
    loadPresets,
    addPreset,
    removePreset,
    setDefault,
    onRecordingStarted,
    onRecordingStopped,
    onCameraOffline,
    onCameraOnline,
  }
})
