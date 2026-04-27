import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listDevices, triggerScan } from '@/api/devices'

export const useDevicesStore = defineStore('devices', () => {
  const items = ref([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const loading = ref(false)
  const scanning = ref(false)

  async function fetchDevices(params = {}) {
    loading.value = true
    try {
      const { data } = await listDevices({ page: page.value, page_size: pageSize.value, ...params })
      items.value = data.items
      total.value = data.total
    } finally {
      loading.value = false
    }
  }

  function changePage(p) {
    page.value = p
    fetchDevices()
  }

  function changePageSize(ps) {
    pageSize.value = ps
    page.value = 1
    fetchDevices()
  }

  async function scan() {
    scanning.value = true
    await triggerScan()
  }

  function onScanCompleted() {
    scanning.value = false
    fetchDevices()
  }

  return { items, total, page, pageSize, loading, scanning, fetchDevices, changePage, changePageSize, scan, onScanCompleted }
})
