import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCamerasStore } from '@/stores/cameras'
import api from '@/api/index'

vi.mock('@/api/index', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('useCamerasStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('has correct initial state', () => {
    const store = useCamerasStore()
    expect(store.items).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.presets).toEqual({})
    expect(store.defaultPresetId).toEqual({})
  })

  it('fetchCameras sets items', async () => {
    const mockCameras = [
      { device_mac: 'AA:BB:CC:DD:EE:FF', name: 'Camera 1' },
      { device_mac: '11:22:33:44:55:66', name: 'Camera 2' },
    ]
    api.get.mockResolvedValue({ data: mockCameras })

    const store = useCamerasStore()
    await store.fetchCameras()

    expect(store.items).toEqual(mockCameras)
    expect(api.get).toHaveBeenCalledWith('/cameras')
  })

  it('loadPresets sets presets and defaultPresetId', async () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    const mockPresets = [
      { id: 1, name: 'Preset 1' },
      { id: 2, name: 'Preset 2' },
    ]
    const mockDefaultPresetId = 1

    api.get
      .mockResolvedValueOnce({ data: mockPresets }) // listPresets
      .mockResolvedValueOnce({ data: { default_preset_id: mockDefaultPresetId } }) // getCamera

    const store = useCamerasStore()
    await store.loadPresets(mac)

    expect(store.presets[mac]).toEqual(mockPresets)
    expect(store.defaultPresetId[mac]).toBe(mockDefaultPresetId)
  })

  it('loadPresets handles 404 with fallback', async () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    const mockPresets = [{ id: 1, name: 'Preset 1' }]
    const error404 = { response: { status: 404 } }

    // Mock based on URL to handle parallel Promise.all calls
    api.get.mockImplementation((url) => {
      if (url.includes('/presets')) {
        return Promise.resolve({ data: mockPresets })
      }
      if (url.includes(mac)) {
        return Promise.reject(error404)
      }
      return Promise.reject(new Error('Unexpected URL'))
    })

    const store = useCamerasStore()
    await store.loadPresets(mac)

    expect(store.presets[mac]).toEqual(mockPresets)
    expect(store.defaultPresetId[mac]).toBeUndefined()
  })

  it('onRecordingStarted updates camera is_recording', () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    const store = useCamerasStore()
    store.items = [{ device_mac: mac, name: 'Camera 1', is_recording: false }]

    store.onRecordingStarted(mac)

    expect(store.items[0].is_recording).toBe(true)
  })

  it('onRecordingStopped updates camera is_recording', () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    const store = useCamerasStore()
    store.items = [{ device_mac: mac, name: 'Camera 1', is_recording: true }]

    store.onRecordingStopped(mac)

    expect(store.items[0].is_recording).toBe(false)
  })

  it('onCameraOffline updates camera is_online', () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    const store = useCamerasStore()
    store.items = [{ device_mac: mac, name: 'Camera 1', is_online: true }]

    store.onCameraOffline(mac)

    expect(store.items[0].is_online).toBe(false)
  })

  it('onCameraOnline updates camera is_online', () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    const store = useCamerasStore()
    store.items = [{ device_mac: mac, name: 'Camera 1', is_online: false }]

    store.onCameraOnline(mac)

    expect(store.items[0].is_online).toBe(true)
  })
})
