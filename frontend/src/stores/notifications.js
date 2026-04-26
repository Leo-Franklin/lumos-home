import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useDevicesStore } from './devices'
import { useCamerasStore } from './cameras'

export const useNotificationsStore = defineStore('notifications', () => {
  const messages = ref([])
  const lastRecordingEvent = ref(null)

  function handle(msg) {
    messages.value.unshift(msg)
    if (messages.value.length > 50) messages.value.pop()

    const devicesStore = useDevicesStore()
    const camerasStore = useCamerasStore()

    switch (msg.event) {
      case 'scan_completed':
        devicesStore.onScanCompleted()
        break
      case 'device_online':
      case 'device_offline':
        devicesStore.fetchDevices()
        break
      case 'recording_started':
        camerasStore.onRecordingStarted(msg.data?.camera_mac)
        break
      case 'recording_completed':
      case 'recording_failed':
        camerasStore.onRecordingStopped(msg.data?.camera_mac)
        lastRecordingEvent.value = { event: msg.event, ...msg.data, _t: Date.now() }
        break
    }
  }

  return { messages, handle, lastRecordingEvent }
})
