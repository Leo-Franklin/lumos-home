import packageJson from '../../package.json'

/** Frontend release version — keep in sync via package.json */
export const APP_VERSION = packageJson.version

/** Extract version string from health / API payloads */
export function pickAppVersion(payload) {
  if (!payload || typeof payload !== 'object') return ''
  const raw = payload.version ?? payload.app_version
  if (raw == null || raw === '') return ''
  return String(raw).trim()
}

/** Normalize to bare semver (strip leading "v") */
export function normalizeAppVersion(version) {
  if (!version) return ''
  return String(version).trim().replace(/^v/i, '')
}

/** User-facing version label */
export function formatAppVersion(version) {
  const normalized = normalizeAppVersion(version)
  return normalized ? `v${normalized}` : '—'
}
