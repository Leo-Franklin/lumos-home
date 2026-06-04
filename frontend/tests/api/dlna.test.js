import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  discoverDLNA,
  listDLNADevices,
  castURL,
  castFile,
  playDevice,
  pauseDevice,
  stopDevice,
  getDeviceStatus,
} from '@/api/dlna'

const mockPost = vi.hoisted(() => vi.fn())
const mockGet = vi.hoisted(() => vi.fn())

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      post: mockPost,
      get: mockGet,
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
  },
}))

describe('dlna API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('discoverDLNA sends POST /dlna/discover', async () => {
    const mockResponse = { data: { devices: [] } }
    mockPost.mockResolvedValue(mockResponse)

    await discoverDLNA()

    expect(mockPost).toHaveBeenCalledWith('/dlna/discover')
  })

  it('listDLNADevices sends GET /dlna', async () => {
    const mockResponse = { data: { devices: [] } }
    mockGet.mockResolvedValue(mockResponse)

    await listDLNADevices()

    expect(mockGet).toHaveBeenCalledWith('/dlna')
  })

  it('castURL sends POST /dlna/cast', async () => {
    const mockResponse = { data: { success: true } }
    mockPost.mockResolvedValue(mockResponse)
    const data = { url: 'http://example.com/video.mp4', deviceId: 'device-1' }

    await castURL(data)

    expect(mockPost).toHaveBeenCalledWith('/dlna/cast', data)
  })

  it('castFile sends POST /dlna/cast/file with multipart form-data', async () => {
    const mockResponse = { data: { success: true } }
    mockPost.mockResolvedValue(mockResponse)
    const formData = new FormData()

    await castFile(formData)

    expect(mockPost).toHaveBeenCalledWith('/dlna/cast/file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
  })

  it('playDevice sends POST /dlna/:deviceId/play', async () => {
    const mockResponse = { data: { status: 'playing' } }
    mockPost.mockResolvedValue(mockResponse)
    const deviceId = 'device-123'

    await playDevice(deviceId)

    expect(mockPost).toHaveBeenCalledWith('/dlna/device-123/play')
  })

  it('pauseDevice sends POST /dlna/:deviceId/pause', async () => {
    const mockResponse = { data: { status: 'paused' } }
    mockPost.mockResolvedValue(mockResponse)
    const deviceId = 'device-123'

    await pauseDevice(deviceId)

    expect(mockPost).toHaveBeenCalledWith('/dlna/device-123/pause')
  })

  it('stopDevice sends POST /dlna/:deviceId/stop', async () => {
    const mockResponse = { data: { status: 'stopped' } }
    mockPost.mockResolvedValue(mockResponse)
    const deviceId = 'device-123'

    await stopDevice(deviceId)

    expect(mockPost).toHaveBeenCalledWith('/dlna/device-123/stop')
  })

  it('getDeviceStatus sends GET /dlna/:deviceId/status', async () => {
    const mockResponse = { data: { status: 'playing' } }
    mockGet.mockResolvedValue(mockResponse)
    const deviceId = 'device-123'

    await getDeviceStatus(deviceId)

    expect(mockGet).toHaveBeenCalledWith('/dlna/device-123/status')
  })
})
