/** Helpers for go2rtc live playback URL/mode selection. */

export function withStreamToken(path, token) {
  if (!path || !token) return path
  const sep = path.includes('?') ? '&' : '?'
  return `${path}${sep}token=${encodeURIComponent(token)}`
}

export function wsUrlFromApiPath(path, token) {
  const withToken = withStreamToken(path, token)
  const loc =
    typeof window !== 'undefined' ? window.location : { protocol: 'http:', host: 'localhost' }
  const wsProto = loc.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${wsProto}//${loc.host}${withToken}`
}

/** Prefer MSE when backend reports it and provides a WebSocket URL. */
export function pickLiveMode(info) {
  if (info?.mode === 'mse' && info?.mse_ws_url) return 'mse'
  return 'mjpeg'
}

export function pickMjpegUrl(info, token) {
  const path = info?.mjpeg_url || ''
  return withStreamToken(path, token)
}
