import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listDLNADevices, discoverDLNA, getDeviceStatus } from '@/api/dlna'

export const useDLNAStore = defineStore('dlna', () => {
  const devices = ref([])
  const loading = ref(false)
  const discovering = ref(false)
  const selectedDevice = ref(null)
  const transportState = ref(null)
  const statusLoading = ref(false)

  let discoverTimeoutId = null

  async function fetchDevices() {
    loading.value = true
    try {
      const { data } = await listDLNADevices()
      devices.value = data
      if (selectedDevice.value) {
        const updated = data.find((d) => d.id === selectedDevice.value.id)
        if (updated) selectedDevice.value = updated
      }
    } finally {
      loading.value = false
    }
  }

  async function discover() {
    discovering.value = true
    clearTimeout(discoverTimeoutId)
    discoverTimeoutId = setTimeout(() => {
      discovering.value = false
    }, 30000)
    try {
      await discoverDLNA()
    } catch {
      discovering.value = false
      clearTimeout(discoverTimeoutId)
    }
  }

  function onDiscoverCompleted() {
    clearTimeout(discoverTimeoutId)
    discovering.value = false
    fetchDevices()
  }

  function selectDevice(device) {
    selectedDevice.value = device
    transportState.value = null
    if (device) refreshStatus()
  }

  async function refreshStatus() {
    if (!selectedDevice.value) return
    statusLoading.value = true
    try {
      const { data } = await getDeviceStatus(selectedDevice.value.id)
      transportState.value = data
    } catch {
      transportState.value = null
    } finally {
      statusLoading.value = false
    }
  }

  return {
    devices,
    loading,
    discovering,
    selectedDevice,
    transportState,
    statusLoading,
    fetchDevices,
    discover,
    onDiscoverCompleted,
    selectDevice,
    refreshStatus,
  }
})
