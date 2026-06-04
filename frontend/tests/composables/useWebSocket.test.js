import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'

let lastCallUrl = null

const mockWs = {
  onopen: null,
  onmessage: null,
  onclose: null,
  onerror: null,
  close: vi.fn(),
}

class MockWebSocket {
  constructor(url) {
    lastCallUrl = url
    this.url = url
    this._onopen = null
    this._onmessage = null
    this._onclose = null
    this._onerror = null
  }
  get onopen() { return this._onopen }
  set onopen(fn) { this._onopen = fn; mockWs.onopen = fn }
  get onmessage() { return this._onmessage }
  set onmessage(fn) { this._onmessage = fn; mockWs.onmessage = fn }
  get onclose() { return this._onclose }
  set onclose(fn) { this._onclose = fn; mockWs.onclose = fn }
  get onerror() { return this._onerror }
  set onerror(fn) { this._onerror = fn; mockWs.onerror = fn }
  close() { mockWs.close() }
}

vi.stubGlobal('WebSocket', MockWebSocket)

const mockLocalStorage = {
  getItem: vi.fn(),
  removeItem: vi.fn(),
}
vi.stubGlobal('localStorage', mockLocalStorage)

import { useWebSocket } from '@/composables/useWebSocket'

vi.mock('vue', () => ({
  ref: vi.fn((val) => ({ value: val })),
  onUnmounted: vi.fn(),
}))

describe('useWebSocket', () => {
  let mockOnMessage

  beforeEach(() => {
    mockOnMessage = vi.fn()
    mockWs.onopen = null
    mockWs.onmessage = null
    mockWs.onclose = null
    mockWs.onerror = null
    mockWs.close.mockClear()
    mockLocalStorage.getItem.mockClear()
    lastCallUrl = null
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should set connected to true on open', async () => {
    mockLocalStorage.getItem.mockReturnValue('fake-token')
    const { connected } = useWebSocket('wss://example.com/ws', { onMessage: mockOnMessage })

    expect(connected.value).toBe(false)
    mockWs.onopen()
    expect(connected.value).toBe(true)
  })

  it('should set connected to false on close', async () => {
    mockLocalStorage.getItem.mockReturnValue('fake-token')
    const { connected } = useWebSocket('wss://example.com/ws', { onMessage: mockOnMessage })

    mockWs.onopen()
    expect(connected.value).toBe(true)
    mockWs.onclose()
    expect(connected.value).toBe(false)
  })

  it('should call onMessage with parsed JSON', async () => {
    mockLocalStorage.getItem.mockReturnValue('fake-token')
    useWebSocket('wss://example.com/ws', { onMessage: mockOnMessage })

    mockWs.onopen()
    const testData = { type: 'test', value: 123 }
    mockWs.onmessage({ data: JSON.stringify(testData) })

    expect(mockOnMessage).toHaveBeenCalledWith(testData)
  })

  it('should ignore malformed JSON in message', async () => {
    mockLocalStorage.getItem.mockReturnValue('fake-token')
    useWebSocket('wss://example.com/ws', { onMessage: mockOnMessage })

    mockWs.onopen()
    mockWs.onmessage({ data: 'not valid json {' })

    expect(mockOnMessage).not.toHaveBeenCalled()
  })

  it('should use token from localStorage in URL', async () => {
    mockLocalStorage.getItem.mockReturnValue('my-auth-token')
    useWebSocket('wss://example.com/ws', { onMessage: mockOnMessage })

    expect(lastCallUrl).toBe('wss://example.com/ws?token=my-auth-token')
  })

  it('should not connect if no token', async () => {
    mockLocalStorage.getItem.mockReturnValue(null)
    const { connected, reconnecting } = useWebSocket('wss://example.com/ws', { onMessage: mockOnMessage })

    expect(mockWs.onopen).toBeNull()
    expect(connected.value).toBe(false)
    expect(reconnecting.value).toBe(false)
  })

  it('should disconnect on cleanup', async () => {
    mockLocalStorage.getItem.mockReturnValue('fake-token')
    const { disconnect } = useWebSocket('wss://example.com/ws', { onMessage: mockOnMessage })

    disconnect()

    expect(mockWs.close).toHaveBeenCalled()
  })
})