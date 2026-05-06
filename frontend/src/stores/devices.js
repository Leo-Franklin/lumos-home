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
  const filterTypes = ref([])
  const search = ref('')
  let searchTimeoutId = null

  async function fetchDevices(params = {}) {
    loading.value = true
    try {
      const query = { page: page.value, page_size: pageSize.value, ...params }
      if (filterTypes.value.length > 0) query.device_type = filterTypes.value.join(',')
      if (search.value.trim()) query.search = search.value.trim()
      const { data } = await listDevices(query)
      items.value = data.items
      total.value = data.total
    } finally {
      loading.value = false
    }
  }

  function setSearch(val) {
    search.value = val
    clearTimeout(searchTimeoutId)
    searchTimeoutId = setTimeout(() => {
      page.value = 1
      fetchDevices()
    }, 300)
  }

  function clearSearch() {
    search.value = ''
    clearTimeout(searchTimeoutId)
    page.value = 1
    fetchDevices()
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

  function toggleFilter(type) {
    if (type === '') {
      filterTypes.value = []
      search.value = ''
    } else {
      const idx = filterTypes.value.indexOf(type)
      filterTypes.value = idx === -1
        ? [...filterTypes.value, type]
        : filterTypes.value.filter((t) => t !== type)
    }
    page.value = 1
    fetchDevices()
  }

  let scanTimeoutId = null

  async function scan() {
    scanning.value = true
    clearTimeout(scanTimeoutId)
    scanTimeoutId = setTimeout(() => {
      scanning.value = false
    }, 60000)
    try {
      await triggerScan()
    } catch {
      scanning.value = false
      clearTimeout(scanTimeoutId)
    }
  }

  function onScanCompleted() {
    clearTimeout(scanTimeoutId)
    scanning.value = false
    fetchDevices()
  }

  return { items, total, page, pageSize, loading, scanning, filterTypes, search, fetchDevices, changePage, changePageSize, toggleFilter, setSearch, clearSearch, scan, onScanCompleted }
})
