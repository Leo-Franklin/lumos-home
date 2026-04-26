import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listDevices, triggerScan } from '@/api/devices'

export const useDevicesStore = defineStore('devices', () => {
  const items = ref([])
  const total = ref(0)
  const loading = ref(false)
  const scanning = ref(false)

  async function fetchDevices(params = {}) {
    loading.value = true
    try {
      const { data } = await listDevices({ page: 1, page_size: 50, ...params })
      items.value = data.items
      total.value = data.total
    } finally {
      loading.value = false
    }
  }

  async function scan() {
    scanning.value = true
    await triggerScan()
  }

  function onScanCompleted() {
    scanning.value = false
    fetchDevices()
  }

  return { items, total, loading, scanning, fetchDevices, scan, onScanCompleted }
})
