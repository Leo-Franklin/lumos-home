import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDLNAStore } from '@/stores/dlna'
import api from '@/api/index'

vi.mock('@/api/index', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

describe('useDLNAStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('has correct initial state', () => {
    const store = useDLNAStore()
    expect(store.devices).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.discovering).toBe(false)
    expect(store.selectedDevice).toBe(null)
    expect(store.transportState).toBe(null)
    expect(store.statusLoading).toBe(false)
  })

  it('fetchDevices sets devices', async () => {
    const mockDevices = [{ id: '1', name: 'TV' }]
    api.get.mockResolvedValue({ data: mockDevices })

    const store = useDLNAStore()
    await store.fetchDevices()

    expect(store.devices).toEqual(mockDevices)
    expect(store.loading).toBe(false)
  })

  it('fetchDevices updates selectedDevice if still in list', async () => {
    const originalDevice = { id: '1', name: 'TV' }
    const updatedDevice = { id: '1', name: 'Smart TV' }
    api.get.mockResolvedValue({ data: [updatedDevice] })

    const store = useDLNAStore()
    store.selectedDevice = originalDevice
    await store.fetchDevices()

    expect(store.selectedDevice).toEqual(updatedDevice)
  })

  it('discover sets discovering true', async () => {
    api.post.mockResolvedValue({})

    const store = useDLNAStore()
    store.discover()

    expect(store.discovering).toBe(true)
  })

  it('onDiscoverCompleted clears discovering and fetches devices', async () => {
    const mockDevices = [{ id: '1', name: 'TV' }]
    api.get.mockResolvedValue({ data: mockDevices })

    const store = useDLNAStore()
    await store.onDiscoverCompleted()

    expect(store.discovering).toBe(false)
    expect(store.devices).toEqual(mockDevices)
  })

  it('selectDevice sets selectedDevice and refreshes status', async () => {
    const device = { id: '1', name: 'TV' }
    api.get.mockResolvedValue({ data: { state: 'playing' } })

    const store = useDLNAStore()
    await store.selectDevice(device)

    expect(store.selectedDevice).toEqual(device)
    expect(store.transportState).toEqual({ state: 'playing' })
  })

  it('refreshStatus does nothing if no selectedDevice', async () => {
    const store = useDLNAStore()
    store.selectedDevice = null

    await store.refreshStatus()

    expect(api.get).not.toHaveBeenCalled()
    expect(store.statusLoading).toBe(false)
  })

  it('refreshStatus sets transportState', async () => {
    const device = { id: '1', name: 'TV' }
    const mockStatus = { state: 'playing' }
    api.get.mockResolvedValue({ data: mockStatus })

    const store = useDLNAStore()
    store.selectedDevice = device
    await store.refreshStatus()

    expect(store.transportState).toEqual(mockStatus)
    expect(store.statusLoading).toBe(false)
  })

  it('refreshStatus sets transportState to null on error', async () => {
    const device = { id: '1', name: 'TV' }
    api.get.mockRejectedValue(new Error('Network error'))

    const store = useDLNAStore()
    store.selectedDevice = device
    await store.refreshStatus()

    expect(store.transportState).toBe(null)
    expect(store.statusLoading).toBe(false)
  })
})
