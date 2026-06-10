import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDevicesStore } from '@/stores/devices'
import api from '@/api/index'

vi.mock('@/api/index', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

describe('useDevicesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('has correct initial state', () => {
    const store = useDevicesStore()
    expect(store.items).toEqual([])
    expect(store.total).toBe(0)
    expect(store.page).toBe(1)
    expect(store.pageSize).toBe(20)
    expect(store.loading).toBe(false)
    expect(store.scanning).toBe(false)
    expect(store.scanningProgress).toBe(0)
    expect(store.scanningStage).toBe('')
    expect(store.filterTypes).toEqual([])
    expect(store.filterOnline).toBe(null)
    expect(store.search).toBe('')
  })

  it('fetchDevices sets items and total', async () => {
    const mockData = {
      items: [{ mac: '00:11:22:33:44:55', name: 'Device 1' }],
      total: 1,
    }
    api.get.mockResolvedValue({ data: mockData })

    const store = useDevicesStore()
    await store.fetchDevices()

    expect(store.items).toEqual(mockData.items)
    expect(store.total).toEqual(mockData.total)
  })

  it('fetchDevices sets loading true while fetching', async () => {
    let loadingDuringFetch = null
    api.get.mockImplementation(() => {
      loadingDuringFetch = useDevicesStore().loading
      return Promise.resolve({ data: { items: [], total: 0 } })
    })

    const store = useDevicesStore()
    const fetchPromise = store.fetchDevices()

    expect(loadingDuringFetch).toBe(true)

    await fetchPromise
    expect(store.loading).toBe(false)
  })

  it('changePage updates page and fetches', async () => {
    api.get.mockResolvedValue({ data: { items: [], total: 0 } })

    const store = useDevicesStore()
    store.changePage(3)

    expect(store.page).toBe(3)
    expect(api.get).toHaveBeenCalled()
  })

  it('changePageSize updates pageSize and resets page', async () => {
    api.get.mockResolvedValue({ data: { items: [], total: 0 } })

    const store = useDevicesStore()
    store.page = 5
    store.changePageSize(50)

    expect(store.pageSize).toBe(50)
    expect(store.page).toBe(1)
    expect(api.get).toHaveBeenCalled()
  })

  it('toggleFilter adds type if not present', async () => {
    api.get.mockResolvedValue({ data: { items: [], total: 0 } })

    const store = useDevicesStore()
    store.toggleFilter('wifi')

    expect(store.filterTypes).toEqual(['wifi'])
  })

  it('toggleFilter removes type if already present', async () => {
    api.get.mockResolvedValue({ data: { items: [], total: 0 } })

    const store = useDevicesStore()
    store.filterTypes = ['wifi', 'zigbee']
    store.toggleFilter('wifi')

    expect(store.filterTypes).toEqual(['zigbee'])
  })

  it('toggleFilter with empty string clears type filters only', async () => {
    api.get.mockResolvedValue({ data: { items: [], total: 0 } })

    const store = useDevicesStore()
    store.filterTypes = ['wifi', 'zigbee']
    store.search = 'test'
    store.toggleFilter('')

    expect(store.filterTypes).toEqual([])
    expect(store.search).toBe('test')
  })

  it('scan calls triggerScan API', async () => {
    api.post.mockResolvedValue({ data: { success: true } })

    const store = useDevicesStore()
    await store.scan()

    expect(api.post).toHaveBeenCalledWith('/devices/scan')
    // Cleanup: scan() schedules a setInterval — cancel it to avoid leaking
    // timers into the next test.
    store.cancelScan()
  })

  it('cancelScan resets scanning state', () => {
    const store = useDevicesStore()
    store.scanning = true
    store.scanningProgress = 50
    store.scanningStage = '192.168.1.x'

    store.cancelScan()

    expect(store.scanning).toBe(false)
    expect(store.scanningProgress).toBe(0)
    expect(store.scanningStage).toBe('')
  })

  it('onScanCompleted fetches devices', async () => {
    api.get.mockResolvedValue({ data: { items: [], total: 0 } })

    const store = useDevicesStore()
    store.onScanCompleted()

    expect(api.get).toHaveBeenCalled()
  })

  it('fetchDevices passes online filter to API', async () => {
    api.get.mockResolvedValue({ data: { items: [], total: 0 } })

    const store = useDevicesStore()
    store.filterOnline = true
    await store.fetchDevices()

    expect(api.get).toHaveBeenCalledWith('/devices', {
      params: expect.objectContaining({ online: true }),
    })
  })

  it('setOnlineFilter updates filter and fetches', async () => {
    api.get.mockResolvedValue({ data: { items: [], total: 0 } })

    const store = useDevicesStore()
    store.setOnlineFilter(false)

    expect(store.filterOnline).toBe(false)
    expect(store.page).toBe(1)
    expect(api.get).toHaveBeenCalled()
  })

  it('clearAllFilters resets search, types, and online filter', async () => {
    api.get.mockResolvedValue({ data: { items: [], total: 0 } })

    const store = useDevicesStore()
    store.filterTypes = ['phone']
    store.filterOnline = true
    store.search = 'test'
    store.page = 3
    store.clearAllFilters()

    expect(store.filterTypes).toEqual([])
    expect(store.filterOnline).toBe(null)
    expect(store.search).toBe('')
    expect(store.page).toBe(1)
    expect(api.get).toHaveBeenCalled()
  })
})
