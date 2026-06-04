import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  getOnlineTrend,
  getDeviceTypeStats,
  getResponseTime,
  getRecordingCalendar,
  getNewDevices,
  getDeviceStability,
  getTypeActivity,
} from '@/api/analytics'

const mockGet = vi.hoisted(() => vi.fn())

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      post: vi.fn(),
      get: mockGet,
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
  },
}))

describe('analytics API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('getOnlineTrend sends GET /analytics/online-trend with params', async () => {
    const params = { start: '2024-01-01', end: '2024-01-31' }
    mockGet.mockResolvedValue({ data: {} })

    await getOnlineTrend(params)

    expect(mockGet).toHaveBeenCalledWith('/analytics/online-trend', { params })
  })

  it('getDeviceTypeStats sends GET /analytics/device-type-stats', async () => {
    mockGet.mockResolvedValue({ data: {} })

    await getDeviceTypeStats()

    expect(mockGet).toHaveBeenCalledWith('/analytics/device-type-stats')
  })

  it('getResponseTime sends GET /analytics/response-time', async () => {
    mockGet.mockResolvedValue({ data: {} })

    await getResponseTime()

    expect(mockGet).toHaveBeenCalledWith('/analytics/response-time')
  })

  it('getRecordingCalendar sends GET /analytics/recording-calendar with params', async () => {
    const params = { year: 2024, month: 1 }
    mockGet.mockResolvedValue({ data: {} })

    await getRecordingCalendar(params)

    expect(mockGet).toHaveBeenCalledWith('/analytics/recording-calendar', { params })
  })

  it('getNewDevices sends GET /analytics/new-devices with params', async () => {
    const params = { days: 30 }
    mockGet.mockResolvedValue({ data: {} })

    await getNewDevices(params)

    expect(mockGet).toHaveBeenCalledWith('/analytics/new-devices', { params })
  })

  it('getDeviceStability sends GET /analytics/device-stability with params', async () => {
    const params = { deviceId: '123' }
    mockGet.mockResolvedValue({ data: {} })

    await getDeviceStability(params)

    expect(mockGet).toHaveBeenCalledWith('/analytics/device-stability', { params })
  })

  it('getTypeActivity sends GET /analytics/type-activity with params', async () => {
    const params = { type: 'camera' }
    mockGet.mockResolvedValue({ data: {} })

    await getTypeActivity(params)

    expect(mockGet).toHaveBeenCalledWith('/analytics/type-activity', { params })
  })
})
