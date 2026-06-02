import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createCamera,
  updateCamera,
  deleteCamera,
  probeCamera,
  startRecord,
  stopRecord,
  takeSnapshot,
  startLive,
  stopLive,
  listPresets,
  createPreset,
  updatePreset,
  deletePreset,
  setDefaultPreset,
  mjpegStreamUrl,
  hlsLiveUrl,
} from '@/api/cameras'

/**
 * Composable encapsulating all Camera view actions + transient dialog state.
 *
 * Returns reactive state and action functions so the view component and
 * the four dialogs can share a single source of truth without prop drilling.
 */
export function useCameraActions() {
  const { t } = useI18n()

  // ── Add / Edit form state ──────────────────────────────────────
  const formDialog = ref({ open: false, mode: 'add' }) // 'add' | 'edit'
  const formData = ref({})
  const formSubmitting = ref(false)

  function openAddDialog() {
    formData.value = {
      device_mac: '',
      onvif_host: '',
      onvif_port: 2020,
      onvif_user: 'admin',
      onvif_password: '',
      rtsp_port: 554,
      stream_profile: 'mainStream',
    }
    formDialog.value = { open: true, mode: 'add' }
  }

  function openEditDialog(cam) {
    formData.value = {
      onvif_host: cam.onvif_host,
      onvif_port: cam.onvif_port,
      onvif_user: cam.onvif_user || '',
      onvif_password: '',
      rtsp_port: cam.rtsp_port,
      rtsp_url: cam.rtsp_url || '',
      stream_profile: cam.stream_profile,
      auto_cast_dlna: cam.auto_cast_dlna || null,
      _mac: cam.device_mac,
    }
    formDialog.value = { open: true, mode: 'edit' }
  }

  function closeFormDialog() {
    formDialog.value.open = false
  }

  async function submitFormDialog() {
    if (formDialog.value.mode === 'add') return submitAdd()
    return submitEdit()
  }

  async function submitAdd() {
    formSubmitting.value = true
    try {
      await createCamera(formData.value)
      ElMessage.success(t('cameras.added'))
      formDialog.value.open = false
      return true
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || t('cameras.addFailed'))
      return false
    } finally {
      formSubmitting.value = false
    }
  }

  async function submitEdit() {
    const { _mac, ...payload } = formData.value
    if (!payload.onvif_password) delete payload.onvif_password
    if (!payload.rtsp_url) payload.rtsp_url = null
    formSubmitting.value = true
    try {
      await updateCamera(_mac, payload)
      ElMessage.success(t('cameras.saved'))
      formDialog.value.open = false
      return true
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || t('cameras.saveFailed'))
      return false
    } finally {
      formSubmitting.value = false
    }
  }

  // ── Delete ──────────────────────────────────────────────────────
  async function deleteCameraAction(cam) {
    await ElMessageBox.confirm(
      t('cameras.deleteConfirm', { host: cam.onvif_host }),
      t('common.confirmDelete'),
      { type: 'warning' },
    )
    await deleteCamera(cam.device_mac)
    ElMessage.success(t('cameras.deleted'))
  }

  // ── Probe ───────────────────────────────────────────────────────
  const probeDialog = ref(false)
  const probeResult = ref(null)
  const probeLoading = ref(false)

  async function openProbeDialog(cam) {
    probeLoading.value = true
    probeResult.value = null
    probeDialog.value = true
    try {
      const { data } = await probeCamera(cam.device_mac)
      probeResult.value = data
    } catch (e) {
      ElMessage.error(
        t('cameras.onvifProbeFailed', {
          detail: e.response?.data?.error?.message || e.message,
        }),
      )
      probeDialog.value = false
    } finally {
      probeLoading.value = false
    }
  }

  function closeProbeDialog() {
    probeDialog.value = false
    probeResult.value = null
  }

  // ── Live (MJPEG) ────────────────────────────────────────────────
  const liveDialog = ref(false)
  const liveUrl = ref('')
  const liveTitle = ref('')

  function openLive(cam) {
    if (!cam.rtsp_url) {
      ElMessage.warning(t('cameras.noRtspWarning'))
      return
    }
    liveTitle.value = t('cameras.liveTitle', { host: cam.onvif_host })
    liveUrl.value = mjpegStreamUrl(cam.device_mac)
    liveDialog.value = true
  }

  function closeLive() {
    liveUrl.value = ''
  }

  // ── Snapshot ────────────────────────────────────────────────────
  const snapshotDialog = ref(false)
  const snapshotUrl = ref('')
  const snapshotTitle = ref('')
  const snapshotLoading = ref(false)

  async function takeSnapshotAction(cam) {
    if (!cam.rtsp_url) {
      ElMessage.warning(t('cameras.noRtsp'))
      return
    }
    snapshotLoading.value = true
    snapshotTitle.value = t('cameras.snapshotTitle', { host: cam.onvif_host })
    try {
      const { data } = await takeSnapshot(cam.device_mac)
      if (snapshotUrl.value) URL.revokeObjectURL(snapshotUrl.value)
      snapshotUrl.value = URL.createObjectURL(data)
      snapshotDialog.value = true
    } catch (e) {
      ElMessage.error(t('cameras.snapshotFailed'))
    } finally {
      snapshotLoading.value = false
    }
  }

  function closeSnapshot() {
    if (snapshotUrl.value) {
      URL.revokeObjectURL(snapshotUrl.value)
      snapshotUrl.value = ''
    }
  }

  function downloadSnapshot() {
    const a = document.createElement('a')
    a.href = snapshotUrl.value
    a.download = `snapshot_${Date.now()}.jpg`
    a.click()
  }

  // ── HLS Live ────────────────────────────────────────────────────
  const hlsDialog = ref(false)
  const hlsTitle = ref('')
  const hlsSrc = ref('')
  const hlsStarting = ref(false)
  let hlsMac = ''

  async function openHlsLive(cam) {
    if (!cam.rtsp_url) {
      ElMessage.warning(t('cameras.noRtspWarning'))
      return
    }
    hlsStarting.value = true
    hlsMac = cam.device_mac
    try {
      await startLive(cam.device_mac)
      hlsTitle.value = t('cameras.hlsTitle', { host: cam.onvif_host })
      hlsSrc.value = hlsLiveUrl(cam.device_mac)
      hlsDialog.value = true
    } catch (e) {
      ElMessage.error(t('cameras.hlsStartFailed'))
    } finally {
      hlsStarting.value = false
    }
  }

  async function closeHlsLive() {
    hlsSrc.value = ''
    if (hlsMac) {
      try { await stopLive(hlsMac) } catch { /* ignore */ }
      hlsMac = ''
    }
  }

  // ── Quick record toggle (from row action) ───────────────────────
  async function toggleRecord(cam) {
    try {
      if (cam.is_recording) {
        await stopRecord(cam.device_mac)
        ElMessage.success(t('cameras.recordStopped'))
      } else {
        await startRecord(cam.device_mac)
        ElMessage.success(t('cameras.recordStarted'))
      }
    } catch (e) {
      ElMessage.error(
        e.response?.data?.detail || e.response?.data?.error?.message || t('common.operationFailed'),
      )
    }
  }

  // ── Preset management ───────────────────────────────────────────
  const presetDialog = ref(false)
  const presetCam = ref(null)
  const presetList = ref([])
  const presetLoading = ref(false)
  const presetSaving = ref(false)
  const presetForm = ref({
    name: '',
    resolution: '1920x1080',
    segment_duration: 300,
    bitrate: 4096,
    fps: 25,
  })
  const presetEditing = ref(null)

  function emptyPresetForm() {
    return { name: '', resolution: '1920x1080', segment_duration: 300, bitrate: 4096, fps: 25 }
  }

  async function openPresets(cam) {
    presetCam.value = cam
    presetEditing.value = null
    presetForm.value = emptyPresetForm()
    presetLoading.value = true
    presetDialog.value = true
    try {
      const { data } = await listPresets(cam.device_mac)
      presetList.value = data
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || 'Failed to load presets')
    } finally {
      presetLoading.value = false
    }
  }

  function closePresets() {
    presetDialog.value = false
    presetCam.value = null
    presetList.value = []
  }

  function startPresetAdd() {
    presetEditing.value = null
    presetForm.value = emptyPresetForm()
  }

  function startPresetEdit(preset) {
    presetEditing.value = preset.id
    presetForm.value = {
      name: preset.name,
      resolution: preset.resolution,
      segment_duration: preset.segment_duration,
      bitrate: preset.bitrate,
      fps: preset.fps,
    }
  }

  async function savePreset() {
    if (!presetCam.value) return
    presetSaving.value = true
    try {
      if (presetEditing.value) {
        await updatePreset(presetCam.value.device_mac, presetEditing.value, presetForm.value)
        ElMessage.success(t('cameras.presetUpdated'))
      } else {
        await createPreset(presetCam.value.device_mac, presetForm.value)
        ElMessage.success(t('cameras.presetCreated'))
      }
      const { data } = await listPresets(presetCam.value.device_mac)
      presetList.value = data
      startPresetAdd()
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || 'Failed to save preset')
    } finally {
      presetSaving.value = false
    }
  }

  async function deletePresetAction(preset) {
    if (!presetCam.value) return
    await ElMessageBox.confirm(
      t('cameras.presetDeleteConfirm', { name: preset.name }),
      t('common.confirmDelete'),
      { type: 'warning' },
    )
    try {
      await deletePreset(presetCam.value.device_mac, preset.id)
      const { data } = await listPresets(presetCam.value.device_mac)
      presetList.value = data
      ElMessage.success(t('cameras.presetDeleted'))
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || t('common.operationFailed'))
    }
  }

  async function setDefaultPresetAction(preset) {
    if (!presetCam.value) return
    try {
      await setDefaultPreset(presetCam.value.device_mac, preset.id)
      const { data } = await listPresets(presetCam.value.device_mac)
      presetList.value = data
      ElMessage.success(t('cameras.defaultPresetSet'))
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || 'Failed to set default preset')
    }
  }

  // ── Record dialog (with preset + overrides) ────────────────────
  const recordDialog = ref(false)
  const recordCam = ref(null)
  const recordPresets = ref([])
  const recordSelectedPresetId = ref(null)
  const recordOverrides = ref({ segment_duration: null, bitrate: null, fps: null, resolution: null })
  const recordSaving = ref(false)

  async function openRecordDialog(cam) {
    recordCam.value = cam
    recordSelectedPresetId.value = null
    recordOverrides.value = { segment_duration: null, bitrate: null, fps: null, resolution: null }
    recordDialog.value = true
    try {
      const { data } = await listPresets(cam.device_mac)
      recordPresets.value = data
    } catch {
      recordPresets.value = []
    }
  }

  function closeRecordDialog() {
    recordDialog.value = false
    recordCam.value = null
  }

  async function startRecordWithDialog() {
    if (!recordCam.value) return false
    recordSaving.value = true
    try {
      const overrides = {}
      if (recordOverrides.value.segment_duration) overrides.segment_duration = recordOverrides.value.segment_duration
      if (recordOverrides.value.bitrate) overrides.bitrate = recordOverrides.value.bitrate
      if (recordOverrides.value.fps) overrides.fps = recordOverrides.value.fps
      if (recordOverrides.value.resolution) overrides.resolution = recordOverrides.value.resolution

      await startRecord(recordCam.value.device_mac, {
        preset_id: recordSelectedPresetId.value || undefined,
        overrides: Object.keys(overrides).length ? overrides : undefined,
      })
      ElMessage.success(t('cameras.recordStarted'))
      recordDialog.value = false
      return true
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || t('cameras.recordStartFailed'))
      return false
    } finally {
      recordSaving.value = false
    }
  }

  return {
    // form (add/edit)
    formDialog,
    formData,
    formSubmitting,
    openAddDialog,
    openEditDialog,
    closeFormDialog,
    submitFormDialog,
    // delete
    deleteCameraAction,
    // probe
    probeDialog,
    probeResult,
    probeLoading,
    openProbeDialog,
    closeProbeDialog,
    // live (mjpeg)
    liveDialog,
    liveUrl,
    liveTitle,
    openLive,
    closeLive,
    // snapshot
    snapshotDialog,
    snapshotUrl,
    snapshotTitle,
    snapshotLoading,
    takeSnapshotAction,
    closeSnapshot,
    downloadSnapshot,
    // hls
    hlsDialog,
    hlsTitle,
    hlsSrc,
    hlsStarting,
    openHlsLive,
    closeHlsLive,
    // quick record toggle
    toggleRecord,
    // presets
    presetDialog,
    presetCam,
    presetList,
    presetLoading,
    presetSaving,
    presetForm,
    presetEditing,
    openPresets,
    closePresets,
    startPresetAdd,
    startPresetEdit,
    savePreset,
    deletePresetAction,
    setDefaultPresetAction,
    // record (with dialog)
    recordDialog,
    recordCam,
    recordPresets,
    recordSelectedPresetId,
    recordOverrides,
    recordSaving,
    openRecordDialog,
    closeRecordDialog,
    startRecordWithDialog,
  }
}
