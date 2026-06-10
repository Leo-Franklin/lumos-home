/** Resolve a human-readable label for a device MAC from a lookup map. */
export function resolveDeviceLabel(mac, deviceMap) {
  if (!mac) return '—'
  const entry = deviceMap?.[mac]
  if (!entry) return mac
  if (entry.alias) return entry.alias
  if (entry.hostname) return entry.hostname
  const info = entry.device_info
  if (info?.alias) return info.alias
  if (info?.hostname) return info.hostname
  return mac
}

/** Build a MAC → device record map from a flat device list or bound-device rows. */
export function buildDeviceMap(devices) {
  const map = {}
  for (const d of devices || []) {
    if (d?.mac) map[d.mac] = d
  }
  return map
}
