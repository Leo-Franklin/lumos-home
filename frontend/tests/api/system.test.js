import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getDashboard, getGo2RtcStatus, updateGo2RtcSettings } from '@/api/system'

const mockGet = vi.hoisted(() => vi.fn())
const mockPut = vi.hoisted(() => vi.fn())

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: mockGet,
      put: mockPut,
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
  },
}))

describe('system API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('getDashboard sends GET /dashboard', async () => {
    mockGet.mockResolvedValue({ data: {} })
    await getDashboard()
    expect(mockGet).toHaveBeenCalledWith('/dashboard')
  })

  it('getGo2RtcStatus sends GET /go2rtc', async () => {
    mockGet.mockResolvedValue({ data: { enabled: true } })
    await getGo2RtcStatus()
    expect(mockGet).toHaveBeenCalledWith('/go2rtc')
  })

  it('updateGo2RtcSettings sends PUT /go2rtc', async () => {
    mockPut.mockResolvedValue({ data: { enabled: false } })
    await updateGo2RtcSettings({ enabled: false })
    expect(mockPut).toHaveBeenCalledWith('/go2rtc', { enabled: false })
  })
})
