/**
 * Minimal go2rtc live player (MSE → WebRTC fallback).
 * Protocol aligned with AlexxIT/go2rtc www/video-rtc.js.
 */

const VIDEO_CODECS = ['avc1.640029', 'avc1.64002A', 'avc1.640033', 'mp4a.40.2', 'mp4a.40.5', 'flac']

export function supportedMseCodecs() {
  if (typeof MediaSource === 'undefined') return ''
  return VIDEO_CODECS.filter((c) => MediaSource.isTypeSupported(`video/mp4; codecs="${c}"`)).join()
}

export class Go2RtcPlayer {
  /**
   * @param {HTMLVideoElement} video
   * @param {string} wsUrl absolute ws:// or wss:// URL
   * @param {{ onMode?: (mode: string) => void, onError?: (msg: string) => void }} hooks
   */
  constructor(video, wsUrl, hooks = {}) {
    this.video = video
    this.wsUrl = wsUrl
    this.onMode = hooks.onMode || (() => {})
    this.onError = hooks.onError || (() => {})
    this._ws = null
    this._pc = null
    this._ondata = null
    this._onmessage = {}
    this._mseCodecs = ''
    this._stopped = false
  }

  start() {
    this._stopped = false
    this._connectWs()
  }

  stop() {
    this._stopped = true
    if (this._ws) {
      this._ws.close()
      this._ws = null
    }
    if (this._pc) {
      this._pc.close()
      this._pc = null
    }
    this.video.srcObject = null
    this.video.removeAttribute('src')
  }

  _connectWs() {
    this._ws = new WebSocket(this.wsUrl)
    this._ws.binaryType = 'arraybuffer'
    this._ws.addEventListener('open', () => this._onWsOpen())
    this._ws.addEventListener('close', () => {
      if (!this._stopped) setTimeout(() => this._connectWs(), 2000)
    })
  }

  _send(obj) {
    if (this._ws?.readyState === WebSocket.OPEN) this._ws.send(JSON.stringify(obj))
  }

  _onWsOpen() {
    this._ondata = null
    this._onmessage = {}
    this._ws.addEventListener('message', (ev) => {
      if (typeof ev.data === 'string') {
        const msg = JSON.parse(ev.data)
        for (const key of Object.keys(this._onmessage)) this._onmessage[key](msg)
      } else if (this._ondata) {
        this._ondata(ev.data)
      }
    })

    if (typeof MediaSource !== 'undefined') {
      this._startMse()
    } else if (typeof RTCPeerConnection !== 'undefined') {
      this._startWebRtc()
    } else {
      this.onError('Browser does not support MSE or WebRTC')
    }
  }

  _startMse() {
    const ms = new MediaSource()
    ms.addEventListener(
      'sourceopen',
      () => {
        this._send({ type: 'mse', value: supportedMseCodecs() })
      },
      { once: true },
    )
    this.video.src = URL.createObjectURL(ms)
    this.video.muted = true
    this.video.play().catch(() => {})

    this._onmessage.mse = (msg) => {
      if (msg.type !== 'mse') return
      this._mseCodecs = msg.value
      this.onMode('MSE')
      const sb = ms.addSourceBuffer(msg.value)
      sb.mode = 'segments'
      let pending = new Uint8Array(0)
      sb.addEventListener('updateend', () => {
        if (!sb.updating && pending.byteLength > 0) {
          const chunk = pending
          pending = new Uint8Array(0)
          try {
            sb.appendBuffer(chunk)
          } catch {
            /* ignore transient append errors */
          }
        }
      })
      this._ondata = (data) => {
        const buf = new Uint8Array(data)
        if (sb.updating || pending.byteLength > 0) {
          const merged = new Uint8Array(pending.byteLength + buf.byteLength)
          merged.set(pending)
          merged.set(buf, pending.byteLength)
          pending = merged
        } else {
          try {
            sb.appendBuffer(buf)
          } catch {
            /* ignore */
          }
        }
      }
    }

    this._onmessage.error = (msg) => {
      if (msg.type === 'error' && String(msg.value || '').startsWith('mse')) {
        this._startWebRtc()
      }
    }
  }

  async _startWebRtc() {
    if (typeof RTCPeerConnection === 'undefined') return
    this.onMode('WebRTC')
    const pc = new RTCPeerConnection({
      bundlePolicy: 'max-bundle',
      iceServers: [{ urls: ['stun:stun.l.google.com:19302'] }],
    })
    this._pc = pc
    pc.addTransceiver('video', { direction: 'recvonly' })
    pc.addTransceiver('audio', { direction: 'recvonly' })
    pc.addEventListener('track', (ev) => {
      if (!this.video.srcObject) this.video.srcObject = new MediaStream()
      this.video.srcObject.addTrack(ev.track)
      this.video.play().catch(() => {})
    })
    pc.addEventListener('icecandidate', (ev) => {
      const candidate = ev.candidate ? ev.candidate.toJSON().candidate : ''
      this._send({ type: 'webrtc/candidate', value: candidate })
    })
    this._onmessage.webrtc = (msg) => {
      if (msg.type === 'webrtc/answer') {
        pc.setRemoteDescription({ type: 'answer', sdp: msg.value }).catch(() => {})
      } else if (msg.type === 'webrtc/candidate' && msg.value) {
        pc.addIceCandidate({ candidate: msg.value, sdpMid: '0' }).catch(() => {})
      }
    }
    const offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    this._send({ type: 'webrtc/offer', value: offer.sdp })
  }
}
