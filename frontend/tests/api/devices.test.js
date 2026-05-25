import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  listDevices,
  triggerScan,
  getDevice,
  updateDevice,
  deleteDevice,
  getTopology,
  getDeviceHeatmap,
} from '@/api/devices'

const mockGet = vi.hoisted(() => vi.fn())
const mockPost = vi.hoisted(() => vi.fn())
const mockPatch = vi.hoisted(() => vi.fn())
const mockDelete = vi.hoisted(() => vi.fn())

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: mockGet,
      post: mockPost,
      patch: mockPatch,
      delete: mockDelete,
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
  },
}))

describe('devices API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('listDevices sends GET /devices with params', async () => {
    const mockResponse = { data: [{ mac: '00:11:22:33:44:55' }] }
    const params = { type: 'wifi' }
    mockGet.mockResolvedValue(mockResponse)

    const result = await listDevices(params)

    expect(mockGet).toHaveBeenCalledWith('/devices', { params })
    expect(result).toEqual(mockResponse)
  })

  it('triggerScan sends POST /devices/scan', async () => {
    mockPost.mockResolvedValue({ data: { success: true } })

    await triggerScan()

    expect(mockPost).toHaveBeenCalledWith('/devices/scan')
  })

  it('getDevice sends GET /devices/:mac', async () => {
    const mac = '00:11:22:33:44:55'
    const mockResponse = { data: { mac } }
    mockGet.mockResolvedValue(mockResponse)

    const result = await getDevice(mac)

    expect(mockGet).toHaveBeenCalledWith(`/devices/${mac}`)
    expect(result).toEqual(mockResponse)
  })

  it('updateDevice sends PATCH /devices/:mac', async () => {
    const mac = '00:11:22:33:44:55'
    const data = { name: 'Updated Device' }
    const mockResponse = { data: { mac, ...data } }
    mockPatch.mockResolvedValue(mockResponse)

    const result = await updateDevice(mac, data)

    expect(mockPatch).toHaveBeenCalledWith(`/devices/${mac}`, data)
    expect(result).toEqual(mockResponse)
  })

  it('deleteDevice sends DELETE /devices/:mac', async () => {
    const mac = '00:11:22:33:44:55'
    mockDelete.mockResolvedValue({ data: { success: true } })

    await deleteDevice(mac)

    expect(mockDelete).toHaveBeenCalledWith(`/devices/${mac}`)
  })

  it('getTopology sends GET /devices/topology', async () => {
    const mockResponse = { data: { nodes: [], links: [] } }
    mockGet.mockResolvedValue(mockResponse)

    const result = await getTopology()

    expect(mockGet).toHaveBeenCalledWith('/devices/topology')
    expect(result).toEqual(mockResponse)
  })

  it('getDeviceHeatmap sends GET /devices/heatmap with params', async () => {
    const mockResponse = { data: { heatmap: [] } }
    const params = { floor: 1 }
    mockGet.mockResolvedValue(mockResponse)

    const result = await getDeviceHeatmap(params)

    expect(mockGet).toHaveBeenCalledWith('/devices/heatmap', { params })
    expect(result).toEqual(mockResponse)
  })
})
