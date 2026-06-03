import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  listRecordings,
  getRecording,
  deleteRecording,
  streamUrl,
  downloadUrl,
  requestRecordingHls,
  recordingHlsUrl,
  getRecordingStats,
  openRecordingFolder,
} from '@/api/recordings'

const mockGet = vi.hoisted(() => vi.fn())
const mockPost = vi.hoisted(() => vi.fn())
const mockDelete = vi.hoisted(() => vi.fn())

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: mockGet,
      post: mockPost,
      delete: mockDelete,
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
  },
}))

describe('recordings API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('listRecordings sends GET /recordings with params', async () => {
    const mockResponse = { data: [] }
    mockGet.mockResolvedValue(mockResponse)

    const params = { cameraId: 1, start: '2024-01-01', end: '2024-01-31' }
    await listRecordings(params)

    expect(mockGet).toHaveBeenCalledWith('/recordings', { params })
  })

  it('getRecording sends GET /recordings/:id', async () => {
    const mockResponse = { data: { id: 1, name: 'test-recording' } }
    mockGet.mockResolvedValue(mockResponse)

    await getRecording(1)

    expect(mockGet).toHaveBeenCalledWith('/recordings/1')
  })

  it('deleteRecording sends DELETE /recordings/:id', async () => {
    mockDelete.mockResolvedValue({})

    await deleteRecording(1)

    expect(mockDelete).toHaveBeenCalledWith('/recordings/1')
  })

  it('streamUrl returns stream URL', () => {
    const url = streamUrl(1)
    expect(url).toBe('/api/v1/recordings/1/stream')
  })

  it('downloadUrl returns download URL', () => {
    const url = downloadUrl(1)
    expect(url).toBe('/api/v1/recordings/1/download')
  })

  it('requestRecordingHls sends GET /recordings/:id/hls/index.m3u8', async () => {
    mockGet.mockResolvedValue({})

    await requestRecordingHls(1)

    expect(mockGet).toHaveBeenCalledWith('/recordings/1/hls/index.m3u8')
  })

  it('recordingHlsUrl returns HLS URL with token', () => {
    localStorage.setItem('token', 'test-token')
    const url = recordingHlsUrl(1)
    expect(url).toBe('/api/v1/recordings/1/hls/index.m3u8?token=test-token')
  })

  it('getRecordingStats sends GET /recordings/stats with params', async () => {
    const mockResponse = { data: { total: 100 } }
    mockGet.mockResolvedValue(mockResponse)

    const params = { cameraId: 1 }
    await getRecordingStats(params)

    expect(mockGet).toHaveBeenCalledWith('/recordings/stats', { params })
  })

  it('openRecordingFolder sends POST /recordings/:id/open-folder', async () => {
    mockPost.mockResolvedValue({})

    await openRecordingFolder(1)

    expect(mockPost).toHaveBeenCalledWith('/recordings/1/open-folder')
  })
})