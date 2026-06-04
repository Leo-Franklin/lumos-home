import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useNotificationsStore } from '@/stores/notifications'

vi.mock('element-plus', () => ({
  ElNotification: vi.fn(),
}))

vi.mock('@/stores/devices', () => ({
  useDevicesStore: vi.fn(() => ({
    fetchDevices: vi.fn(),
    onScanCompleted: vi.fn(),
  })),
}))

vi.mock('@/stores/cameras', () => ({
  useCamerasStore: vi.fn(() => ({
    fetchDevices: vi.fn(),
    onScanCompleted: vi.fn(),
    onCameraOffline: vi.fn(),
    onCameraOnline: vi.fn(),
    onRecordingStarted: vi.fn(),
    onRecordingStopped: vi.fn(),
  })),
}))

vi.mock('@/stores/members', () => ({
  useMembersStore: vi.fn(() => ({
    onPresenceEvent: vi.fn(),
  })),
}))

vi.mock('@/stores/dlna', () => ({
  useDLNAStore: vi.fn(() => ({
    onDiscoverCompleted: vi.fn(),
    refreshStatus: vi.fn(),
  })),
}))

describe('useNotificationsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('has correct initial state', () => {
    const store = useNotificationsStore()
    expect(store.messages).toEqual([])
    expect(store.lastRecordingEvent).toBeNull()
  })

  it('handle adds message to messages array', () => {
    const store = useNotificationsStore()
    const msg = { event: 'test_event', data: { foo: 'bar' } }
    store.handle(msg)
    expect(store.messages).toHaveLength(1)
    expect(store.messages[0]).toEqual(msg)
  })

  it('handle limits messages to 50', () => {
    const store = useNotificationsStore()
    for (let i = 0; i < 55; i++) {
      store.handle({ event: `event_${i}`, data: { index: i } })
    }
    expect(store.messages).toHaveLength(50)
    expect(store.messages[0].event).toBe('event_54')
    expect(store.messages[49].event).toBe('event_5')
  })

  it('handle stores lastRecordingEvent for recording_completed', () => {
    const store = useNotificationsStore()
    const msg = {
      event: 'recording_completed',
      data: { camera_mac: 'AA:BB:CC:DD:EE:FF', duration: 120 },
    }
    store.handle(msg)
    expect(store.lastRecordingEvent).toBeTruthy()
    expect(store.lastRecordingEvent.event).toBe('recording_completed')
    expect(store.lastRecordingEvent.camera_mac).toBe('AA:BB:CC:DD:EE:FF')
    expect(store.lastRecordingEvent.duration).toBe(120)
    expect(store.lastRecordingEvent._t).toBeTruthy()
  })

  it('handle stores lastRecordingEvent for recording_failed', () => {
    const store = useNotificationsStore()
    const msg = {
      event: 'recording_failed',
      data: { camera_mac: '11:22:33:44:55:66', error: 'disk full' },
    }
    store.handle(msg)
    expect(store.lastRecordingEvent).toBeTruthy()
    expect(store.lastRecordingEvent.event).toBe('recording_failed')
    expect(store.lastRecordingEvent.camera_mac).toBe('11:22:33:44:55:66')
    expect(store.lastRecordingEvent.error).toBe('disk full')
    expect(store.lastRecordingEvent._t).toBeTruthy()
  })
})
