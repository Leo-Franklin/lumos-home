/** Pick initial stream index after probe: prefer saved URL, then auto-detected, then first valid. */
export function resolveInitialStreamIndex(profiles, { currentRtspUrl, autoSetRtspUrl } = {}) {
  if (!profiles?.length) return null

  if (currentRtspUrl) {
    const matched = profiles.find((p) => p.rtsp_url === currentRtspUrl)
    if (matched) return matched.index
  }

  if (autoSetRtspUrl) {
    const matched = profiles.find((p) => p.rtsp_url === autoSetRtspUrl)
    if (matched) return matched.index
  }

  const firstValid = profiles.find((p) => p.rtsp_url)
  return firstValid?.index ?? profiles[0].index
}

export function isStreamSelectable(profile) {
  return Boolean(profile?.rtsp_url)
}
