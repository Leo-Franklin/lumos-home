/** Shared notification preference keys — read by settings UI and notifications store. */
export const NOTIFY_EVENT_KEYS = [
  'unknown_device_detected',
  'camera_online',
  'camera_offline',
  'recording_completed',
  'recording_failed',
  'member_arrived',
  'member_left',
  'scan_completed',
]

export const DEFAULT_NOTIFY_EVENTS = Object.fromEntries(
  NOTIFY_EVENT_KEYS.map((key) => [
    key,
    key === 'member_arrived' || key === 'member_left' || key === 'scan_completed' ? false : true,
  ]),
)

const STORAGE_EVENTS = 'pref:notify-events'
const STORAGE_SOUND = 'pref:notify-sound'

export function loadNotifyEvents() {
  try {
    const raw = localStorage.getItem(STORAGE_EVENTS)
    if (!raw) return { ...DEFAULT_NOTIFY_EVENTS }
    return { ...DEFAULT_NOTIFY_EVENTS, ...JSON.parse(raw) }
  } catch {
    return { ...DEFAULT_NOTIFY_EVENTS }
  }
}

export function saveNotifyEvents(events) {
  localStorage.setItem(STORAGE_EVENTS, JSON.stringify(events))
}

export function isNotifyEventEnabled(event) {
  const events = loadNotifyEvents()
  return events[event] !== false
}

export function loadNotifySound() {
  return localStorage.getItem(STORAGE_SOUND) === '1'
}

export function saveNotifySound(enabled) {
  localStorage.setItem(STORAGE_SOUND, enabled ? '1' : '0')
}
