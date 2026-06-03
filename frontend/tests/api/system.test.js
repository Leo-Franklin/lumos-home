import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getDashboard } from '@/api/system'

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

describe('system API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('getDashboard sends GET /dashboard', async () => {
    const mockResponse = { data: { members_home: 0 } }
    mockGet.mockResolvedValue(mockResponse)

    const result = await getDashboard()

    expect(mockGet).toHaveBeenCalledWith('/dashboard')
    expect(result).toEqual(mockResponse)
  })
})