<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
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

const { t } = useI18n()
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

// P2-10: Esc 键优先取消当前打开的 dialog（替代全屏捕获，仅 CameraView 范围）
function handleKeydown(e) {
  if (e.key !== 'Escape') return
  // 优先取消最后打开的 dialog
  if (recordDialog.value) closeRecordDialog()
  else if (presetDialog.value) closePresets()
  else if (hlsDialog.value) closeHlsLive()
  else if (liveDialog.value) closeLive()
  else if (snapshotDialog.value) closeSnapshot()
  else if (formDialog.value?.open) closeFormDialog()
  else if (probeDialog.value) closeProbeDialog()
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  Promise.all([
    camerasStore.fetchCameras(),
    devicesStore.fetchDevices(),
    dlnaStore.fetchDevices(),
  ])
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
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

    <!-- P2-10: 全部 5 个 dialog 改用 v-if lazy mount，不打开时不挂载，节省内存 -->
    <CameraFormDialog
      v-if="formDialog.open"
      v-model="formDialog.open"
      :mode="formDialog.mode"
      :form="formData"
      :submitting="formSubmitting"
      @submit="handleFormSubmit"
      @cancel="closeFormDialog"
    />

    <CameraProbeDialog
      v-if="probeDialog"
      v-model="probeDialog"
      :loading="probeLoading"
      :result="probeResult"
    />

    <el-dialog
      v-if="liveDialog"
      v-model="liveDialog"
      :title="liveTitle"
      width="720px"
      :destroy-on-close="true"
      @close="closeLive"
    >
      <CameraPlayer v-if="liveDialog && liveUrl" mode="live" :src="liveUrl" />
    </el-dialog>

    <el-dialog
      v-if="snapshotDialog"
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
      v-if="hlsDialog"
      v-model="hlsDialog"
      :title="hlsTitle"
      width="720px"
      :destroy-on-close="true"
      @close="closeHlsLive"
    >
      <CameraPlayer v-if="hlsDialog && hlsSrc" mode="hls" :src="hlsSrc" />
    </el-dialog>

    <CameraPresetDialog
      v-if="presetDialog"
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
      v-if="recordDialog"
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
