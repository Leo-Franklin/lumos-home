import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElNotification } from 'element-plus'
import { useDevicesStore } from './devices'
import { useCamerasStore } from './cameras'
import { useMembersStore } from './members'
import { useDLNAStore } from './dlna'

export const useNotificationsStore = defineStore('notifications', () => {
  const messages = ref([])
  const lastRecordingEvent = ref(null)

  function handle(msg) {
    messages.value.unshift(msg)
    if (messages.value.length > 50) messages.value.pop()

    const devicesStore = useDevicesStore()
    const camerasStore = useCamerasStore()
    const membersStore = useMembersStore()
    const dlnaStore = useDLNAStore()

    switch (msg.event) {
      case 'scan_completed':
        devicesStore.onScanCompleted()
        break
      case 'device_online':
      case 'device_offline':
        devicesStore.fetchDevices()
        break
      case 'unknown_device_detected': {
        const d = msg.data || {}
        const label = d.hostname || d.vendor || d.mac || '未知设备'
        ElNotification({
          title: '发现陌生设备',
          message: `${label}（${d.ip || ''}）首次出现在局域网，请前往设备页面确认`,
          type: 'warning',
          duration: 8000,
        })
        devicesStore.fetchDevices()
        break
      }
      case 'camera_offline': {
        const mac = msg.data?.mac
        camerasStore.onCameraOffline(mac)
        ElNotification({
          title: '摄像头掉线',
          message: `摄像头 ${mac || ''} 已离线，请检查设备连接`,
          type: 'error',
          duration: 8000,
        })
        break
      }
      case 'camera_online': {
        const mac = msg.data?.mac
        camerasStore.onCameraOnline(mac)
        ElNotification({
          title: '摄像头恢复',
          message: `摄像头 ${mac || ''} 已重新上线`,
          type: 'success',
          duration: 5000,
        })
        break
      }
      case 'recording_started':
        camerasStore.onRecordingStarted(msg.data?.camera_mac)
        break
      case 'recording_completed':
      case 'recording_failed':
        camerasStore.onRecordingStopped(msg.data?.camera_mac)
        lastRecordingEvent.value = { event: msg.event, ...msg.data, _t: Date.now() }
        break
      case 'member_arrived':
      case 'member_left':
        membersStore.onPresenceEvent(msg.data?.member_id, msg.event)
        break
      case 'dlna_discover_completed':
        dlnaStore.onDiscoverCompleted()
        break
      case 'dlna_cast_started':
        dlnaStore.refreshStatus()
        break
    }
  }

  return { messages, handle, lastRecordingEvent }
})
