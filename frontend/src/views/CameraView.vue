<script setup>
import { onMounted } from 'vue'
import { useCamerasStore } from '@/stores/cameras'
import { useDevicesStore } from '@/stores/devices'
import { useDLNAStore } from '@/stores/dlna'
import { useCameraActions } from '@/composables/useCameraActions'
import { Plus } from '@element-plus/icons-vue'
import CameraPlayer from '@/components/CameraPlayer.vue'
import CameraTable from '@/components/cameras/CameraTable.vue'
import CameraFormDialog from '@/components/cameras/CameraFormDialog.vue'
import CameraProbeDialog from '@/components/cameras/CameraProbeDialog.vue'
import CameraPresetDialog from '@/components/cameras/CameraPresetDialog.vue'
import CameraRecordDialog from '@/components/cameras/CameraRecordDialog.vue'

const camerasStore = useCamerasStore()
const devicesStore = useDevicesStore()
const dlnaStore = useDLNAStore()

const {
  formDialog, formData, formSubmitting,
  openAddDialog, openEditDialog, closeFormDialog, submitFormDialog,
  deleteCameraAction,
  probeDialog, probeResult, probeLoading, openProbeDialog, closeProbeDialog,
  liveDialog, liveUrl, liveTitle, openLive, closeLive,
  snapshotDialog, snapshotUrl, snapshotTitle,
  takeSnapshotAction, closeSnapshot, downloadSnapshot,
  hlsDialog, hlsTitle, hlsSrc, openHlsLive, closeHlsLive,
  toggleRecord,
  presetDialog, presetCam, presetList, presetLoading, presetSaving,
  presetForm, presetEditing,
  openPresets, closePresets, startPresetAdd, startPresetEdit,
  savePreset, deletePresetAction, setDefaultPresetAction,
  recordDialog, recordCam, recordPresets, recordSelectedPresetId,
  recordOverrides, recordSaving,
  openRecordDialog, closeRecordDialog, startRecordWithDialog,
} = useCameraActions()

async function refreshAfterMutation() { await camerasStore.fetchCameras() }

function handlePreviewCommand(cmd, row) {
  if (cmd === 'live') openLive(row)
  else if (cmd === 'snapshot') takeSnapshotAction(row)
  else if (cmd === 'hls') openHlsLive(row)
}

function handleMoreCommand(cmd, row) {
  if (cmd === 'probe') openProbeDialog(row)
  else if (cmd === 'presets') openPresets(row)
  else if (cmd === 'delete') deleteCameraAction(row).then(refreshAfterMutation).catch(() => {})
}

async function handleFormSubmit() {
  const ok = await submitFormDialog()
  if (ok) await refreshAfterMutation()
}

async function handleRecordClick(row) {
  if (row.is_recording) {
    await toggleRecord(row)
    await refreshAfterMutation()
  } else {
    openRecordDialog(row)
  }
}

async function handleStartRecord() {
  const ok = await startRecordWithDialog()
  if (ok) await refreshAfterMutation()
}

onMounted(async () => {
  await Promise.all([
    camerasStore.fetchCameras(),
    devicesStore.fetchDevices(),
    dlnaStore.fetchDevices(),
  ])
})
</script>

<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">{{ $t('cameras.title') }}</h2>
      <el-button type="primary" :icon="Plus" @click="openAddDialog">
        {{ $t('cameras.addCamera') }}
      </el-button>
    </div>

    <CameraTable
      :cameras="camerasStore.items"
      :loading="camerasStore.loading"
      @edit="openEditDialog"
      @record="handleRecordClick"
      @preview="handlePreviewCommand"
      @more="handleMoreCommand"
    />

    <CameraFormDialog
      v-model="formDialog.open"
      :mode="formDialog.mode"
      :form="formData"
      :submitting="formSubmitting"
      @submit="handleFormSubmit"
      @cancel="closeFormDialog"
    />

    <CameraProbeDialog
      v-model="probeDialog"
      :loading="probeLoading"
      :result="probeResult"
    />

    <el-dialog
      v-model="liveDialog"
      :title="liveTitle"
      width="720px"
      :destroy-on-close="true"
      @close="closeLive"
    >
      <CameraPlayer v-if="liveDialog && liveUrl" mode="live" :src="liveUrl" />
    </el-dialog>

    <el-dialog
      v-model="snapshotDialog"
      :title="snapshotTitle"
      width="720px"
      :destroy-on-close="true"
      @close="closeSnapshot"
    >
      <img v-if="snapshotUrl" :src="snapshotUrl" class="snapshot-img" />
      <template #footer>
        <el-button @click="snapshotDialog = false">{{ $t('common.close') }}</el-button>
        <el-button type="primary" @click="downloadSnapshot">{{ $t('common.download') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="hlsDialog"
      :title="hlsTitle"
      width="720px"
      :destroy-on-close="true"
      @close="closeHlsLive"
    >
      <CameraPlayer v-if="hlsDialog && hlsSrc" mode="hls" :src="hlsSrc" />
    </el-dialog>

    <CameraPresetDialog
      v-model="presetDialog"
      :camera="presetCam"
      :list="presetList"
      :loading="presetLoading"
      :saving="presetSaving"
      :form="presetForm"
      :editing="presetEditing"
      @add="startPresetAdd"
      @edit="startPresetEdit"
      @save="savePreset().then(refreshAfterMutation)"
      @delete="deletePresetAction"
      @setDefault="setDefaultPresetAction"
      @update:modelValue="(v) => { if (!v) closePresets() }"
    />

    <CameraRecordDialog
      v-model="recordDialog"
      :camera="recordCam"
      :presets="recordPresets"
      v-model:selected-preset-id="recordSelectedPresetId"
      v-model:overrides="recordOverrides"
      :saving="recordSaving"
      @start="handleStartRecord"
      @update:modelValue="(v) => { if (!v) closeRecordDialog() }"
    />
  </div>
</template>

<style scoped>
.snapshot-img {
  width: 100%;
  display: block;
  border-radius: 4px;
}
</style>
