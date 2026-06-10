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
  const scanningProgress = ref(0)
  const scanningStage = ref('')
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
      filterTypes.value =
        idx === -1 ? [...filterTypes.value, type] : filterTypes.value.filter((t) => t !== type)
    }
    page.value = 1
    fetchDevices()
  }

  let scanTimeoutId = null
  let scanProgressTimer = null

  async function scan() {
    scanning.value = true
    scanningProgress.value = 0
    scanningStage.value = '192.168.1.x'
    clearTimeout(scanTimeoutId)
    clearInterval(scanProgressTimer)
    // Safety net: stop scanning after 60s if backend never reports completion.
    scanTimeoutId = setTimeout(() => {
      scanning.value = false
      scanningProgress.value = 0
      scanningStage.value = ''
      clearInterval(scanProgressTimer)
      scanProgressTimer = null
    }, 60000)
    // Optimistic progress simulation until backend reports real progress.
    // The backend currently doesn't push progress events, so we interpolate
    // up to 95% to give the user visible feedback.
    scanProgressTimer = setInterval(() => {
      if (scanningProgress.value < 95) {
        scanningProgress.value = Math.min(95, scanningProgress.value + 5)
      }
    }, 2000)
    try {
      await triggerScan()
    } catch {
      scanning.value = false
      scanningProgress.value = 0
      scanningStage.value = ''
      clearTimeout(scanTimeoutId)
      clearInterval(scanProgressTimer)
      scanProgressTimer = null
    }
  }

  // Mock: backend has no cancel endpoint yet, but the UI surface is required.
  // Locally reset state — the real scan still runs to completion in the
  // background and onScanCompleted will clear the remaining refs.
  function cancelScan() {
    clearTimeout(scanTimeoutId)
    clearInterval(scanProgressTimer)
    scanProgressTimer = null
    scanning.value = false
    scanningProgress.value = 0
    scanningStage.value = ''
  }

  function onScanStarted(subnet) {
    if (subnet) scanningStage.value = subnet
  }

  function onScanCompleted() {
    clearTimeout(scanTimeoutId)
    clearInterval(scanProgressTimer)
    scanProgressTimer = null
    scanning.value = false
    scanningProgress.value = 100
    scanningStage.value = ''
    fetchDevices()
  }

  return {
    items,
    total,
    page,
    pageSize,
    loading,
    scanning,
    scanningProgress,
    scanningStage,
    filterTypes,
    search,
    fetchDevices,
    changePage,
    changePageSize,
    toggleFilter,
    setSearch,
    clearSearch,
    scan,
    cancelScan,
    onScanStarted,
    onScanCompleted,
  }
})
