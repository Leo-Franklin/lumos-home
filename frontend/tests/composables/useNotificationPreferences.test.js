import { describe, it, expect, beforeEach } from 'vitest'
import {
  DEFAULT_NOTIFY_EVENTS,
  loadNotifyEvents,
  saveNotifyEvents,
  isNotifyEventEnabled,
  loadNotifySound,
  saveNotifySound,
} from '@/composables/useNotificationPreferences'

describe('useNotificationPreferences', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('returns defaults when storage is empty', () => {
    expect(loadNotifyEvents()).toEqual(DEFAULT_NOTIFY_EVENTS)
    expect(loadNotifySound()).toBe(false)
  })

  it('persists and reads event toggles', () => {
    const events = { ...DEFAULT_NOTIFY_EVENTS, camera_offline: false }
    saveNotifyEvents(events)
    expect(loadNotifyEvents().camera_offline).toBe(false)
    expect(isNotifyEventEnabled('camera_offline')).toBe(false)
    expect(isNotifyEventEnabled('camera_online')).toBe(true)
  })

  it('persists sound preference', () => {
    saveNotifySound(true)
    expect(loadNotifySound()).toBe(true)
    saveNotifySound(false)
    expect(loadNotifySound()).toBe(false)
  })
})
