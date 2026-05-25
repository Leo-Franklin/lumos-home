import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  listCameras,
  createCamera,
  getCamera,
  updateCamera,
  deleteCamera,
  probeCamera,
  startRecord,
  stopRecord,
  listPresets,
  createPreset,
  updatePreset,
  deletePreset,
  setDefaultPreset,
  mjpegStreamUrl,
  takeSnapshot,
  startLive,
  stopLive,
  hlsLiveUrl,
} from '@/api/cameras'

const mockGet = vi.hoisted(() => vi.fn())
const mockPost = vi.hoisted(() => vi.fn())
const mockPut = vi.hoisted(() => vi.fn())
const mockDelete = vi.hoisted(() => vi.fn())

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: mockGet,
      post: mockPost,
      put: mockPut,
      delete: mockDelete,
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
  },
}))

describe('cameras API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.setItem('token', 'test-token')
  })

  it('listCameras sends GET /cameras', async () => {
    mockGet.mockResolvedValue({ data: [] })
    await listCameras()
    expect(mockGet).toHaveBeenCalledWith('/cameras')
  })

  it('createCamera sends POST /cameras', async () => {
    const data = { name: 'Camera 1' }
    mockPost.mockResolvedValue({ data })
    await createCamera(data)
    expect(mockPost).toHaveBeenCalledWith('/cameras', data)
  })

  it('getCamera sends GET /cameras/:mac', async () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    mockGet.mockResolvedValue({ data: {} })
    await getCamera(mac)
    expect(mockGet).toHaveBeenCalledWith(`/cameras/${mac}`)
  })

  it('updateCamera sends PUT /cameras/:mac', async () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    const data = { name: 'Updated Camera' }
    mockPut.mockResolvedValue({ data })
    await updateCamera(mac, data)
    expect(mockPut).toHaveBeenCalledWith(`/cameras/${mac}`, data)
  })

  it('deleteCamera sends DELETE /cameras/:mac', async () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    mockDelete.mockResolvedValue({})
    await deleteCamera(mac)
    expect(mockDelete).toHaveBeenCalledWith(`/cameras/${mac}`)
  })

  it('probeCamera sends POST /cameras/:mac/probe', async () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    mockPost.mockResolvedValue({})
    await probeCamera(mac)
    expect(mockPost).toHaveBeenCalledWith(`/cameras/${mac}/probe`)
  })

  it('startRecord sends POST /cameras/:mac/record/start with preset_id and overrides', async () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    const opts = { preset_id: 1, overrides: { fps: 30 } }
    mockPost.mockResolvedValue({})
    await startRecord(mac, opts)
    expect(mockPost).toHaveBeenCalledWith(`/cameras/${mac}/record/start`, {
      preset_id: opts.preset_id,
      overrides: opts.overrides,
    })
  })

  it('stopRecord sends POST /cameras/:mac/record/stop', async () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    mockPost.mockResolvedValue({})
    await stopRecord(mac)
    expect(mockPost).toHaveBeenCalledWith(`/cameras/${mac}/record/stop`)
  })

  it('listPresets sends GET /cameras/:mac/presets', async () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    mockGet.mockResolvedValue({ data: [] })
    await listPresets(mac)
    expect(mockGet).toHaveBeenCalledWith(`/cameras/${mac}/presets`)
  })

  it('createPreset sends POST /cameras/:mac/presets', async () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    const data = { name: 'Preset 1', position: { pan: 0, tilt: 0 } }
    mockPost.mockResolvedValue({ data })
    await createPreset(mac, data)
    expect(mockPost).toHaveBeenCalledWith(`/cameras/${mac}/presets`, data)
  })

  it('updatePreset sends PUT /cameras/:mac/presets/:presetId', async () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    const presetId = 1
    const data = { name: 'Updated Preset' }
    mockPut.mockResolvedValue({ data })
    await updatePreset(mac, presetId, data)
    expect(mockPut).toHaveBeenCalledWith(`/cameras/${mac}/presets/${presetId}`, data)
  })

  it('deletePreset sends DELETE /cameras/:mac/presets/:presetId', async () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    const presetId = 1
    mockDelete.mockResolvedValue({})
    await deletePreset(mac, presetId)
    expect(mockDelete).toHaveBeenCalledWith(`/cameras/${mac}/presets/${presetId}`)
  })

  it('setDefaultPreset sends POST /cameras/:mac/presets/default (uppercase mac)', async () => {
    const mac = 'aa:bb:cc:dd:ee:ff'
    const presetId = 1
    mockPost.mockResolvedValue({})
    await setDefaultPreset(mac, presetId)
    expect(mockPost).toHaveBeenCalledWith(`/cameras/${mac.toUpperCase()}/presets/default`, {
      preset_id: presetId,
    })
  })

  it('mjpegStreamUrl returns URL with token', () => {
    localStorage.setItem('token', 'my-token')
    const mac = 'AA:BB:CC:DD:EE:FF'
    const url = mjpegStreamUrl(mac)
    expect(url).toBe(`/api/v1/cameras/${mac}/stream/mjpeg?token=${encodeURIComponent('my-token')}`)
  })

  it('takeSnapshot sends GET /cameras/:mac/snapshot with blob responseType', async () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    mockGet.mockResolvedValue({ data: new Blob() })
    await takeSnapshot(mac)
    expect(mockGet).toHaveBeenCalledWith(`/cameras/${mac}/snapshot`, { responseType: 'blob' })
  })

  it('startLive sends POST /cameras/:mac/live/start', async () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    mockPost.mockResolvedValue({})
    await startLive(mac)
    expect(mockPost).toHaveBeenCalledWith(`/cameras/${mac}/live/start`)
  })

  it('stopLive sends DELETE /cameras/:mac/live/stop', async () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    mockDelete.mockResolvedValue({})
    await stopLive(mac)
    expect(mockDelete).toHaveBeenCalledWith(`/cameras/${mac}/live/stop`)
  })

  it('hlsLiveUrl returns HLS URL', () => {
    const mac = 'AA:BB:CC:DD:EE:FF'
    const url = hlsLiveUrl(mac)
    expect(url).toBe(`/hls/${mac}/index.m3u8`)
  })
})
