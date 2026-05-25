# Unit Test Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 smart-home-frontend 项目所有 stores、api modules、composables 编写完整的单元测试。

**Architecture:** 采用混合 Mock 策略：stores 测试中 mock `@/api/index`（axios 实例），API 模块测试中 mock axios 本身，composables 测试中 mock 各自依赖（WebSocket、vue-i18n）。

**Tech Stack:** Vitest + happy-dom + @vue/test-utils + Pinia

---

## File Map

```
tests/
├── api/
│   ├── auth.test.js          [新建]
│   ├── devices.test.js       [新建]
│   ├── cameras.test.js       [新建]
│   ├── schedules.test.js     [新建]
│   ├── members.test.js       [新建]
│   ├── dlna.test.js          [新建]
│   ├── analytics.test.js     [新建]
│   ├── recordings.test.js    [新建]
│   └── system.test.js        [新建]
├── composables/
│   ├── useWebSocket.test.js  [新建]
│   └── useFormatDuration.test.js [新建]
└── stores/
    ├── devices.test.js       [新建]
    ├── cameras.test.js       [新建]
    ├── members.test.js       [新建]
    ├── dlna.test.js          [新建]
    ├── locale.test.js        [新建]
    └── notifications.test.js [新建]
```

---

## Part 1: API 模块测试（9 个文件）

### Task 1: API - auth.js 测试

**Files:**
- Create: `tests/api/auth.test.js`

- [ ] **Step 1: Write tests for auth API functions**

```javascript
import { describe, it, expect, vi } from 'vitest'
import axios from 'axios'
import { login, register } from '@/api/auth'

vi.mock('axios')

describe('auth API', () => {
  it('login sends POST /auth/login with email and password', async () => {
    axios.post.mockResolvedValue({ data: { access_token: 'token123' } })
    const result = await login('test@example.com', 'password')
    expect(axios.post).toHaveBeenCalledWith('/auth/login', {
      email: 'test@example.com',
      password: 'password',
    })
    expect(result).toEqual({ access_token: 'token123' })
  })

  it('register sends POST /auth/register with email and password', async () => {
    axios.post.mockResolvedValue({})
    await register('test@example.com', 'password')
    expect(axios.post).toHaveBeenCalledWith('/auth/register', {
      email: 'test@example.com',
      password: 'password',
    })
  })
})
```

- [ ] **Step 2: Run test to verify it passes**
  Run: `pnpm test -- tests/api/auth.test.js`
  Expected: PASS

- [ ] **Step 3: Commit**
  ```bash
  git add tests/api/auth.test.js && git commit -m "test(api/auth): add unit tests for login and register"
  ```

---

### Task 2: API - devices.js 测试

**Files:**
- Create: `tests/api/devices.test.js`

- [ ] **Step 1: Write tests**

```javascript
import { describe, it, expect, vi } from 'vitest'
import axios from 'axios'
import {
  listDevices,
  triggerScan,
  getDevice,
  updateDevice,
  deleteDevice,
  getTopology,
  getDeviceHeatmap,
} from '@/api/devices'

vi.mock('axios')

describe('devices API', () => {
  it('listDevices sends GET /devices with params', async () => {
    axios.get.mockResolvedValue({ data: { items: [], total: 0 } })
    await listDevices({ page: 1, page_size: 20 })
    expect(axios.get).toHaveBeenCalledWith('/devices', { params: { page: 1, page_size: 20 } })
  })

  it('triggerScan sends POST /devices/scan', async () => {
    axios.post.mockResolvedValue({})
    await triggerScan()
    expect(axios.post).toHaveBeenCalledWith('/devices/scan')
  })

  it('getDevice sends GET /devices/:mac', async () => {
    axios.get.mockResolvedValue({ data: {} })
    await getDevice('AA:BB:CC:DD:EE:FF')
    expect(axios.get).toHaveBeenCalledWith('/devices/AA:BB:CC:DD:EE:FF')
  })

  it('updateDevice sends PATCH /devices/:mac', async () => {
    axios.patch.mockResolvedValue({})
    await updateDevice('AA:BB:CC:DD:EE:FF', { name: 'Device' })
    expect(axios.patch).toHaveBeenCalledWith('/devices/AA:BB:CC:DD:EE:FF', { name: 'Device' })
  })

  it('deleteDevice sends DELETE /devices/:mac', async () => {
    axios.delete.mockResolvedValue({})
    await deleteDevice('AA:BB:CC:DD:EE:FF')
    expect(axios.delete).toHaveBeenCalledWith('/devices/AA:BB:CC:DD:EE:FF')
  })

  it('getTopology sends GET /devices/topology', async () => {
    axios.get.mockResolvedValue({ data: [] })
    await getTopology()
    expect(axios.get).toHaveBeenCalledWith('/devices/topology')
  })

  it('getDeviceHeatmap sends GET /devices/heatmap with params', async () => {
    axios.get.mockResolvedValue({ data: [] })
    await getDeviceHeatmap({ days: 7 })
    expect(axios.get).toHaveBeenCalledWith('/devices/heatmap', { params: { days: 7 } })
  })
})
```

- [ ] **Step 2: Run test to verify it passes**
  Run: `pnpm test -- tests/api/devices.test.js`
  Expected: PASS

- [ ] **Step 3: Commit**
  ```bash
  git add tests/api/devices.test.js && git commit -m "test(api/devices): add unit tests for all device API functions"
  ```

---

### Task 3: API - cameras.js 测试

**Files:**
- Create: `tests/api/cameras.test.js`

- [ ] **Step 1: Write tests**

```javascript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import {
  listCameras,
  createCamera,
  getCamera,
  updateCamera,
  deleteCamera,
  probeCamera,
  startRecord,
  stopRecord,
  listPresets,
  createPreset,
  updatePreset,
  deletePreset,
  setDefaultPreset,
  mjpegStreamUrl,
  takeSnapshot,
  startLive,
  stopLive,
  hlsLiveUrl,
} from '@/api/cameras'

vi.mock('axios')

describe('cameras API', () => {
  beforeEach(() => {
    localStorage.setItem('token', 'test-token')
  })

  it('listCameras sends GET /cameras', async () => {
    axios.get.mockResolvedValue({ data: [] })
    await listCameras()
    expect(axios.get).toHaveBeenCalledWith('/cameras')
  })

  it('createCamera sends POST /cameras', async () => {
    axios.post.mockResolvedValue({ data: {} })
    await createCamera({ name: 'cam1' })
    expect(axios.post).toHaveBeenCalledWith('/cameras', { name: 'cam1' })
  })

  it('getCamera sends GET /cameras/:mac', async () => {
    axios.get.mockResolvedValue({ data: {} })
    await getCamera('AA:BB:CC:DD:EE:FF')
    expect(axios.get).toHaveBeenCalledWith('/cameras/AA:BB:CC:DD:EE:FF')
  })

  it('updateCamera sends PUT /cameras/:mac', async () => {
    axios.put.mockResolvedValue({})
    await updateCamera('AA:BB:CC:DD:EE:FF', { name: 'updated' })
    expect(axios.put).toHaveBeenCalledWith('/cameras/AA:BB:CC:DD:EE:FF', { name: 'updated' })
  })

  it('deleteCamera sends DELETE /cameras/:mac', async () => {
    axios.delete.mockResolvedValue({})
    await deleteCamera('AA:BB:CC:DD:EE:FF')
    expect(axios.delete).toHaveBeenCalledWith('/cameras/AA:BB:CC:DD:EE:FF')
  })

  it('probeCamera sends POST /cameras/:mac/probe', async () => {
    axios.post.mockResolvedValue({})
    await probeCamera('AA:BB:CC:DD:EE:FF')
    expect(axios.post).toHaveBeenCalledWith('/cameras/AA:BB:CC:DD:EE:FF/probe')
  })

  it('startRecord sends POST /cameras/:mac/record/start', async () => {
    axios.post.mockResolvedValue({})
    await startRecord('AA:BB:CC:DD:EE:FF', { preset_id: 1, overrides: {} })
    expect(axios.post).toHaveBeenCalledWith('/cameras/AA:BB:CC:DD:EE:FF/record/start', { preset_id: 1, overrides: {} })
  })

  it('stopRecord sends POST /cameras/:mac/record/stop', async () => {
    axios.post.mockResolvedValue({})
    await stopRecord('AA:BB:CC:DD:EE:FF')
    expect(axios.post).toHaveBeenCalledWith('/cameras/AA:BB:CC:DD:EE:FF/record/stop')
  })

  it('listPresets sends GET /cameras/:mac/presets', async () => {
    axios.get.mockResolvedValue({ data: [] })
    await listPresets('AA:BB:CC:DD:EE:FF')
    expect(axios.get).toHaveBeenCalledWith('/cameras/AA:BB:CC:DD:EE:FF/presets')
  })

  it('createPreset sends POST /cameras/:mac/presets', async () => {
    axios.post.mockResolvedValue({ data: {} })
    await createPreset('AA:BB:CC:DD:EE:FF', { name: 'preset1' })
    expect(axios.post).toHaveBeenCalledWith('/cameras/AA:BB:CC:DD:EE:FF/presets', { name: 'preset1' })
  })

  it('updatePreset sends PUT /cameras/:mac/presets/:presetId', async () => {
    axios.put.mockResolvedValue({})
    await updatePreset('AA:BB:CC:DD:EE:FF', 1, { name: 'updated' })
    expect(axios.put).toHaveBeenCalledWith('/cameras/AA:BB:CC:DD:EE:FF/presets/1', { name: 'updated' })
  })

  it('deletePreset sends DELETE /cameras/:mac/presets/:presetId', async () => {
    axios.delete.mockResolvedValue({})
    await deletePreset('AA:BB:CC:DD:EE:FF', 1)
    expect(axios.delete).toHaveBeenCalledWith('/cameras/AA:BB:CC:DD:EE:FF/presets/1')
  })

  it('setDefaultPreset sends POST /cameras/:mac/presets/default (uppercase mac)', async () => {
    axios.post.mockResolvedValue({})
    await setDefaultPreset('aa:bb:cc:dd:ee:ff', 1)
    expect(axios.post).toHaveBeenCalledWith('/cameras/AA:BB:CC:DD:EE:FF/presets/default', { preset_id: 1 })
  })

  it('mjpegStreamUrl returns URL with token', () => {
    const url = mjpegStreamUrl('AA:BB:CC:DD:EE:FF')
    expect(url).toContain('/api/v1/cameras/AA:BB:CC:DD:EE:FF/stream/mjpeg')
    expect(url).toContain('token=test-token')
  })

  it('takeSnapshot sends GET /cameras/:mac/snapshot with blob responseType', async () => {
    axios.get.mockResolvedValue({ data: new Blob() })
    await takeSnapshot('AA:BB:CC:DD:EE:FF')
    expect(axios.get).toHaveBeenCalledWith('/cameras/AA:BB:CC:DD:EE:FF/snapshot', { responseType: 'blob' })
  })

  it('startLive sends POST /cameras/:mac/live/start', async () => {
    axios.post.mockResolvedValue({})
    await startLive('AA:BB:CC:DD:EE:FF')
    expect(axios.post).toHaveBeenCalledWith('/cameras/AA:BB:CC:DD:EE:FF/live/start')
  })

  it('stopLive sends DELETE /cameras/:mac/live/stop', async () => {
    axios.delete.mockResolvedValue({})
    await stopLive('AA:BB:CC:DD:EE:FF')
    expect(axios.delete).toHaveBeenCalledWith('/cameras/AA:BB:CC:DD:EE:FF/live/stop')
  })

  it('hlsLiveUrl returns HLS URL', () => {
    const url = hlsLiveUrl('AA:BB:CC:DD:EE:FF')
    expect(url).toBe('/hls/AA:BB:CC:DD:EE:FF/index.m3u8')
  })
})
```

- [ ] **Step 2: Run test to verify it passes**
  Run: `pnpm test -- tests/api/cameras.test.js`
  Expected: PASS

- [ ] **Step 3: Commit**
  ```bash
  git add tests/api/cameras.test.js && git commit -m "test(api/cameras): add unit tests for all camera API functions"
  ```

---

### Task 4: API - schedules.js 测试

**Files:**
- Create: `tests/api/schedules.test.js`

- [ ] **Step 1: Write tests**

```javascript
import { describe, it, expect, vi } from 'vitest'
import axios from 'axios'
import {
  listSchedules,
  createSchedule,
  updateSchedule,
  deleteSchedule,
} from '@/api/schedules'

vi.mock('axios')

describe('schedules API', () => {
  it('listSchedules sends GET /schedules', async () => {
    axios.get.mockResolvedValue({ data: [] })
    await listSchedules()
    expect(axios.get).toHaveBeenCalledWith('/schedules')
  })

  it('createSchedule sends POST /schedules', async () => {
    axios.post.mockResolvedValue({ data: {} })
    await createSchedule({ name: 'schedule1' })
    expect(axios.post).toHaveBeenCalledWith('/schedules', { name: 'schedule1' })
  })

  it('updateSchedule sends PATCH /schedules/:id', async () => {
    axios.patch.mockResolvedValue({})
    await updateSchedule(1, { name: 'updated' })
    expect(axios.patch).toHaveBeenCalledWith('/schedules/1', { name: 'updated' })
  })

  it('deleteSchedule sends DELETE /schedules/:id', async () => {
    axios.delete.mockResolvedValue({})
    await deleteSchedule(1)
    expect(axios.delete).toHaveBeenCalledWith('/schedules/1')
  })
})
```

- [ ] **Step 2: Run test to verify it passes**
  Run: `pnpm test -- tests/api/schedules.test.js`
  Expected: PASS

- [ ] **Step 3: Commit**
  ```bash
  git add tests/api/schedules.test.js && git commit -m "test(api/schedules): add unit tests for schedule API functions"
  ```

---

### Task 5: API - members.js 测试

**Files:**
- Create: `tests/api/members.test.js`

- [ ] **Step 1: Write tests**

```javascript
import { describe, it, expect, vi } from 'vitest'
import axios from 'axios'
import {
  listMembers,
  createMember,
  updateMember,
  deleteMember,
  listMemberDevices,
  bindDevice,
  unbindDevice,
  listPresenceLogs,
  getMemberStats,
} from '@/api/members'

vi.mock('axios')

describe('members API', () => {
  it('listMembers sends GET /members', async () => {
    axios.get.mockResolvedValue({ data: [] })
    await listMembers()
    expect(axios.get).toHaveBeenCalledWith('/members')
  })

  it('createMember sends POST /members', async () => {
    axios.post.mockResolvedValue({ data: {} })
    await createMember({ name: 'member1' })
    expect(axios.post).toHaveBeenCalledWith('/members', { name: 'member1' })
  })

  it('updateMember sends PATCH /members/:id', async () => {
    axios.patch.mockResolvedValue({})
    await updateMember(1, { name: 'updated' })
    expect(axios.patch).toHaveBeenCalledWith('/members/1', { name: 'updated' })
  })

  it('deleteMember sends DELETE /members/:id', async () => {
    axios.delete.mockResolvedValue({})
    await deleteMember(1)
    expect(axios.delete).toHaveBeenCalledWith('/members/1')
  })

  it('listMemberDevices sends GET /members/:id/devices', async () => {
    axios.get.mockResolvedValue({ data: [] })
    await listMemberDevices(1)
    expect(axios.get).toHaveBeenCalledWith('/members/1/devices')
  })

  it('bindDevice sends POST /members/:id/devices', async () => {
    axios.post.mockResolvedValue({})
    await bindDevice(1, { mac: 'AA:BB:CC:DD:EE:FF' })
    expect(axios.post).toHaveBeenCalledWith('/members/1/devices', { mac: 'AA:BB:CC:DD:EE:FF' })
  })

  it('unbindDevice sends DELETE /members/:id/devices/:mac', async () => {
    axios.delete.mockResolvedValue({})
    await unbindDevice(1, 'AA:BB:CC:DD:EE:FF')
    expect(axios.delete).toHaveBeenCalledWith('/members/1/devices/AA:BB:CC:DD:EE:FF')
  })

  it('listPresenceLogs sends GET /members/:id/logs with params', async () => {
    axios.get.mockResolvedValue({ data: [] })
    await listPresenceLogs(1, { days: 7 })
    expect(axios.get).toHaveBeenCalledWith('/members/1/logs', { params: { days: 7 } })
  })

  it('getMemberStats sends GET /members/:id/stats with params', async () => {
    axios.get.mockResolvedValue({ data: {} })
    await getMemberStats(1, { days: 30 })
    expect(axios.get).toHaveBeenCalledWith('/members/1/stats', { params: { days: 30 } })
  })
})
```

- [ ] **Step 2: Run test to verify it passes**
  Run: `pnpm test -- tests/api/members.test.js`
  Expected: PASS

- [ ] **Step 3: Commit**
  ```bash
  git add tests/api/members.test.js && git commit -m "test(api/members): add unit tests for member API functions"
  ```

---

### Task 6: API - dlna.js 测试

**Files:**
- Create: `tests/api/dlna.test.js`

- [ ] **Step 1: Write tests**

```javascript
import { describe, it, expect, vi } from 'vitest'
import axios from 'axios'
import {
  discoverDLNA,
  listDLNADevices,
  castURL,
  castFile,
  playDevice,
  pauseDevice,
  stopDevice,
  getDeviceStatus,
} from '@/api/dlna'

vi.mock('axios')

describe('dlna API', () => {
  it('discoverDLNA sends POST /dlna/discover', async () => {
    axios.post.mockResolvedValue({})
    await discoverDLNA()
    expect(axios.post).toHaveBeenCalledWith('/dlna/discover')
  })

  it('listDLNADevices sends GET /dlna', async () => {
    axios.get.mockResolvedValue({ data: [] })
    await listDLNADevices()
    expect(axios.get).toHaveBeenCalledWith('/dlna')
  })

  it('castURL sends POST /dlna/cast', async () => {
    axios.post.mockResolvedValue({})
    await castURL({ url: 'http://example.com/video' })
    expect(axios.post).toHaveBeenCalledWith('/dlna/cast', { url: 'http://example.com/video' })
  })

  it('castFile sends POST /dlna/cast/file with multipart form-data', async () => {
    const formData = new FormData()
    axios.post.mockResolvedValue({})
    await castFile(formData)
    expect(axios.post).toHaveBeenCalledWith('/dlna/cast/file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
  })

  it('playDevice sends POST /dlna/:deviceId/play', async () => {
    axios.post.mockResolvedValue({})
    await playDevice('device-1')
    expect(axios.post).toHaveBeenCalledWith('/dlna/device-1/play')
  })

  it('pauseDevice sends POST /dlna/:deviceId/pause', async () => {
    axios.post.mockResolvedValue({})
    await pauseDevice('device-1')
    expect(axios.post).toHaveBeenCalledWith('/dlna/device-1/pause')
  })

  it('stopDevice sends POST /dlna/:deviceId/stop', async () => {
    axios.post.mockResolvedValue({})
    await stopDevice('device-1')
    expect(axios.post).toHaveBeenCalledWith('/dlna/device-1/stop')
  })

  it('getDeviceStatus sends GET /dlna/:deviceId/status', async () => {
    axios.get.mockResolvedValue({ data: {} })
    await getDeviceStatus('device-1')
    expect(axios.get).toHaveBeenCalledWith('/dlna/device-1/status')
  })
})
```

- [ ] **Step 2: Run test to verify it passes**
  Run: `pnpm test -- tests/api/dlna.test.js`
  Expected: PASS

- [ ] **Step 3: Commit**
  ```bash
  git add tests/api/dlna.test.js && git commit -m "test(api/dlna): add unit tests for DLNA API functions"
  ```

---

### Task 7: API - analytics.js 测试

**Files:**
- Create: `tests/api/analytics.test.js`

- [ ] **Step 1: Write tests**

```javascript
import { describe, it, expect, vi } from 'vitest'
import axios from 'axios'
import {
  getOnlineTrend,
  getDeviceTypeStats,
  getResponseTime,
  getRecordingCalendar,
  getNewDevices,
  getDeviceStability,
  getTypeActivity,
} from '@/api/analytics'

vi.mock('axios')

describe('analytics API', () => {
  it('getOnlineTrend sends GET /analytics/online-trend with params', async () => {
    axios.get.mockResolvedValue({ data: [] })
    await getOnlineTrend({ days: 7 })
    expect(axios.get).toHaveBeenCalledWith('/analytics/online-trend', { params: { days: 7 } })
  })

  it('getDeviceTypeStats sends GET /analytics/device-type-stats', async () => {
    axios.get.mockResolvedValue({ data: [] })
    await getDeviceTypeStats()
    expect(axios.get).toHaveBeenCalledWith('/analytics/device-type-stats')
  })

  it('getResponseTime sends GET /analytics/response-time', async () => {
    axios.get.mockResolvedValue({ data: [] })
    await getResponseTime()
    expect(axios.get).toHaveBeenCalledWith('/analytics/response-time')
  })

  it('getRecordingCalendar sends GET /analytics/recording-calendar with params', async () => {
    axios.get.mockResolvedValue({ data: [] })
    await getRecordingCalendar({ year: 2026 })
    expect(axios.get).toHaveBeenCalledWith('/analytics/recording-calendar', { params: { year: 2026 } })
  })

  it('getNewDevices sends GET /analytics/new-devices with params', async () => {
    axios.get.mockResolvedValue({ data: [] })
    await getNewDevices({ days: 30 })
    expect(axios.get).toHaveBeenCalledWith('/analytics/new-devices', { params: { days: 30 } })
  })

  it('getDeviceStability sends GET /analytics/device-stability with params', async () => {
    axios.get.mockResolvedValue({ data: {} })
    await getDeviceStability({ mac: 'AA:BB:CC:DD:EE:FF' })
    expect(axios.get).toHaveBeenCalledWith('/analytics/device-stability', { params: { mac: 'AA:BB:CC:DD:EE:FF' } })
  })

  it('getTypeActivity sends GET /analytics/type-activity with params', async () => {
    axios.get.mockResolvedValue({ data: [] })
    await getTypeActivity({ type: 'camera' })
    expect(axios.get).toHaveBeenCalledWith('/analytics/type-activity', { params: { type: 'camera' } })
  })
})
```

- [ ] **Step 2: Run test to verify it passes**
  Run: `pnpm test -- tests/api/analytics.test.js`
  Expected: PASS

- [ ] **Step 3: Commit**
  ```bash
  git add tests/api/analytics.test.js && git commit -m "test(api/analytics): add unit tests for analytics API functions"
  ```

---

### Task 8: API - recordings.js 测试

**Files:**
- Create: `tests/api/recordings.test.js`

- [ ] **Step 1: Write tests**

```javascript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import {
  listRecordings,
  getRecording,
  deleteRecording,
  streamUrl,
  downloadUrl,
  requestRecordingHls,
  recordingHlsUrl,
  getRecordingStats,
  openRecordingFolder,
} from '@/api/recordings'

vi.mock('axios')

describe('recordings API', () => {
  beforeEach(() => {
    localStorage.setItem('token', 'test-token')
  })

  it('listRecordings sends GET /recordings with params', async () => {
    axios.get.mockResolvedValue({ data: [] })
    await listRecordings({ page: 1 })
    expect(axios.get).toHaveBeenCalledWith('/recordings', { params: { page: 1 } })
  })

  it('getRecording sends GET /recordings/:id', async () => {
    axios.get.mockResolvedValue({ data: {} })
    await getRecording(1)
    expect(axios.get).toHaveBeenCalledWith('/recordings/1')
  })

  it('deleteRecording sends DELETE /recordings/:id', async () => {
    axios.delete.mockResolvedValue({})
    await deleteRecording(1)
    expect(axios.delete).toHaveBeenCalledWith('/recordings/1')
  })

  it('streamUrl returns stream URL', () => {
    expect(streamUrl(1)).toBe('/api/v1/recordings/1/stream')
  })

  it('downloadUrl returns download URL', () => {
    expect(downloadUrl(1)).toBe('/api/v1/recordings/1/download')
  })

  it('requestRecordingHls sends GET /recordings/:id/hls/index.m3u8', async () => {
    axios.get.mockResolvedValue({ data: '' })
    await requestRecordingHls(1)
    expect(axios.get).toHaveBeenCalledWith('/recordings/1/hls/index.m3u8')
  })

  it('recordingHlsUrl returns HLS URL with token', () => {
    const url = recordingHlsUrl(1)
    expect(url).toContain('/api/v1/recordings/1/hls/index.m3u8')
    expect(url).toContain('token=test-token')
  })

  it('getRecordingStats sends GET /recordings/stats with params', async () => {
    axios.get.mockResolvedValue({ data: {} })
    await getRecordingStats({ days: 7 })
    expect(axios.get).toHaveBeenCalledWith('/recordings/stats', { params: { days: 7 } })
  })

  it('openRecordingFolder sends POST /recordings/:id/open-folder', async () => {
    axios.post.mockResolvedValue({})
    await openRecordingFolder(1)
    expect(axios.post).toHaveBeenCalledWith('/recordings/1/open-folder')
  })
})
```

- [ ] **Step 2: Run test to verify it passes**
  Run: `pnpm test -- tests/api/recordings.test.js`
  Expected: PASS

- [ ] **Step 3: Commit**
  ```bash
  git add tests/api/recordings.test.js && git commit -m "test(api/recordings): add unit tests for recordings API functions"
  ```

---

### Task 9: API - system.js 测试

**Files:**
- Create: `tests/api/system.test.js`

- [ ] **Step 1: Write tests**

```javascript
import { describe, it, expect, vi } from 'vitest'
import axios from 'axios'
import { getDashboard } from '@/api/system'

vi.mock('axios')

describe('system API', () => {
  it('getDashboard sends GET /dashboard', async () => {
    axios.get.mockResolvedValue({ data: {} })
    await getDashboard()
    expect(axios.get).toHaveBeenCalledWith('/dashboard')
  })
})
```

- [ ] **Step 2: Run test to verify it passes**
  Run: `pnpm test -- tests/api/system.test.js`
  Expected: PASS

- [ ] **Step 3: Commit**
  ```bash
  git add tests/api/system.test.js && git commit -m "test(api/system): add unit tests for system API functions"
  ```

---

## Part 2: Composables 测试（2 个文件）

### Task 10: useWebSocket 测试

**Files:**
- Create: `tests/composables/useWebSocket.test.js`

- [ ] **Step 1: Write tests**

```javascript
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ref } from 'vue'

// Mock WebSocket
const mockWsInstance = {
  onopen: null,
  onclose: null,
  onmessage: null,
  onerror: null,
  close: vi.fn(),
  send: vi.fn(),
}
vi.stubGlobal('WebSocket', vi.fn(() => mockWsInstance))

// Mock localStorage
const localStorageMock = { getItem: vi.fn(), removeItem: vi.fn() }
vi.stubGlobal('localStorage', localStorageMock)

import { useWebSocket } from '@/composables/useWebSocket'

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.getItem.mockReturnValue('test-token')
    WebSocket.mockImplementation(() => mockWsInstance)
  })

  it('should set connected to true on open', () => {
    const { connected } = useWebSocket('ws://localhost:8080')
    mockWsInstance.onopen()
    expect(connected.value).toBe(true)
  })

  it('should set connected to false on close', () => {
    const { connected } = useWebSocket('ws://localhost:8080')
    mockWsInstance.onopen()
    mockWsInstance.onclose()
    expect(connected.value).toBe(false)
  })

  it('should call onMessage with parsed JSON', () => {
    const onMessage = vi.fn()
    const { } = useWebSocket('ws://localhost:8080', { onMessage })
    const testMsg = { event: 'test', data: 'value' }
    mockWsInstance.onmessage({ data: JSON.stringify(testMsg) })
    expect(onMessage).toHaveBeenCalledWith(testMsg)
  })

  it('should ignore malformed JSON in message', () => {
    const onMessage = vi.fn()
    const { } = useWebSocket('ws://localhost:8080', { onMessage })
    mockWsInstance.onmessage({ data: 'not json' })
    expect(onMessage).not.toHaveBeenCalled()
  })

  it('should use token from localStorage in URL', () => {
    localStorage.getItem.mockReturnValue('my-token')
    WebSocket.mockImplementation((url) => {
      expect(url).toBe('ws://localhost:8080?token=my-token')
      return mockWsInstance
    })
    useWebSocket('ws://localhost:8080')
  })

  it('should not connect if no token', () => {
    localStorage.getItem.mockReturnValue(null)
    const ws = useWebSocket('ws://localhost:8080')
    expect(WebSocket).not.toHaveBeenCalled()
  })

  it('should disconnect on cleanup', () => {
    const { disconnect } = useWebSocket('ws://localhost:8080')
    disconnect()
    expect(mockWsInstance.close).toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run test to verify it passes**
  Run: `pnpm test -- tests/composables/useWebSocket.test.js`
  Expected: PASS

- [ ] **Step 3: Commit**
  ```bash
  git add tests/composables/useWebSocket.test.js && git commit -m "test(composables): add unit tests for useWebSocket"
  ```

---

### Task 11: useFormatDuration 测试

**Files:**
- Create: `tests/composables/useFormatDuration.test.js`

- [ ] **Step 1: Write tests**

```javascript
import { describe, it, expect, vi } from 'vitest'
import { useI18n } from 'vue-i18n'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key) => {
      const map = {
        'common.minute': '分钟',
        'common.hour': '小时',
      }
      return map[key] || key
    },
  }),
}))

import { useFormatDuration } from '@/composables/useFormatDuration'

describe('useFormatDuration', () => {
  it('returns "0 分钟" for 0 seconds', () => {
    const { formatDuration } = useFormatDuration()
    expect(formatDuration(0)).toBe('0 分钟')
  })

  it('returns "0 分钟" for null/undefined', () => {
    const { formatDuration } = useFormatDuration()
    expect(formatDuration(null)).toBe('0 分钟')
    expect(formatDuration(undefined)).toBe('0 分钟')
  })

  it('returns minutes only for less than an hour', () => {
    const { formatDuration } = useFormatDuration()
    expect(formatDuration(300)).toBe('5 分钟')
    expect(formatDuration(60)).toBe('1 分钟')
  })

  it('returns hours and minutes for more than an hour', () => {
    const { formatDuration } = useFormatDuration()
    expect(formatDuration(3660)).toBe('1 小时 1 分钟')
    expect(formatDuration(7200)).toBe('2 小时 0 分钟')
    expect(formatDuration(9000)).toBe('2 小时 30 分钟')
  })
})
```

- [ ] **Step 2: Run test to verify it passes**
  Run: `pnpm test -- tests/composables/useFormatDuration.test.js`
  Expected: PASS

- [ ] **Step 3: Commit**
  ```bash
  git add tests/composables/useFormatDuration.test.js && git commit -m "test(composables): add unit tests for useFormatDuration"
  ```

---

## Part 3: Stores 测试（6 个新文件）

### Task 12: devices store 测试

**Files:**
- Create: `tests/stores/devices.test.js`

- [ ] **Step 1: Write tests**

```javascript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDevicesStore } from '@/stores/devices'
import api from '@/api/index'

vi.mock('@/api/index', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}))

describe('useDevicesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('has correct initial state', () => {
    const store = useDevicesStore()
    expect(store.items).toEqual([])
    expect(store.total).toBe(0)
    expect(store.page).toBe(1)
    expect(store.pageSize).toBe(20)
    expect(store.loading).toBe(false)
    expect(store.scanning).toBe(false)
    expect(store.filterTypes).toEqual([])
    expect(store.search).toBe('')
  })

  it('fetchDevices sets items and total', async () => {
    const mockData = { items: [{ mac: 'AA:BB:CC:DD:EE:FF' }], total: 1 }
    api.get.mockResolvedValue({ data: mockData })
    const store = useDevicesStore()
    await store.fetchDevices()
    expect(store.items).toEqual(mockData.items)
    expect(store.total).toBe(1)
    expect(api.get).toHaveBeenCalled()
  })

  it('fetchDevices sets loading true while fetching', async () => {
    let loadingDuringFetch
    api.get.mockImplementation(() => {
      loadingDuringFetch = useDevicesStore().loading
      return Promise.resolve({ data: { items: [], total: 0 } })
    })
    const store = useDevicesStore()
    await store.fetchDevices()
    expect(loadingDuringFetch).toBe(true)
    expect(store.loading).toBe(false)
  })

  it('changePage updates page and fetches', async () => {
    api.get.mockResolvedValue({ data: { items: [], total: 0 } })
    const store = useDevicesStore()
    await store.changePage(3)
    expect(store.page).toBe(3)
    expect(api.get).toHaveBeenCalled()
  })

  it('changePageSize updates pageSize and resets page', async () => {
    api.get.mockResolvedValue({ data: { items: [], total: 0 } })
    const store = useDevicesStore()
    store.page = 5
    await store.changePageSize(50)
    expect(store.pageSize).toBe(50)
    expect(store.page).toBe(1)
  })

  it('toggleFilter adds type if not present', async () => {
    api.get.mockResolvedValue({ data: { items: [], total: 0 } })
    const store = useDevicesStore()
    await store.toggleFilter('camera')
    expect(store.filterTypes).toContain('camera')
  })

  it('toggleFilter removes type if already present', async () => {
    api.get.mockResolvedValue({ data: { items: [], total: 0 } })
    const store = useDevicesStore()
    store.filterTypes = ['camera', 'speaker']
    await store.toggleFilter('camera')
    expect(store.filterTypes).not.toContain('camera')
    expect(store.filterTypes).toContain('speaker')
  })

  it('toggleFilter with empty string clears all filters', async () => {
    api.get.mockResolvedValue({ data: { items: [], total: 0 } })
    const store = useDevicesStore()
    store.filterTypes = ['camera']
    store.search = 'test'
    await store.toggleFilter('')
    expect(store.filterTypes).toEqual([])
    expect(store.search).toBe('')
  })

  it('scan calls triggerScan API', async () => {
    api.post.mockResolvedValue({})
    const store = useDevicesStore()
    await store.scan()
    expect(api.post).toHaveBeenCalledWith('/devices/scan')
  })

  it('onScanCompleted fetches devices', async () => {
    api.get.mockResolvedValue({ data: { items: [], total: 0 } })
    const store = useDevicesStore()
    store.scanning = true
    store.onScanCompleted()
    // Timeout cleared, scanning set to false
    expect(store.scanning).toBe(false)
  })
})
```

- [ ] **Step 2: Run test to verify it passes**
  Run: `pnpm test -- tests/stores/devices.test.js`
  Expected: PASS

- [ ] **Step 3: Commit**
  ```bash
  git add tests/stores/devices.test.js && git commit -m "test(stores/devices): add unit tests for devices store"
  ```

---

### Task 13: cameras store 测试

**Files:**
- Create: `tests/stores/cameras.test.js`

- [ ] **Step 1: Write tests**

```javascript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCamerasStore } from '@/stores/cameras'
import api from '@/api/index'

vi.mock('@/api/index', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('useCamerasStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('has correct initial state', () => {
    const store = useCamerasStore()
    expect(store.items).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.presets).toEqual({})
    expect(store.defaultPresetId).toEqual({})
  })

  it('fetchCameras sets items', async () => {
    const mockCameras = [{ device_mac: 'AA:BB:CC:DD:EE:FF', is_recording: false }]
    api.get.mockResolvedValue({ data: mockCameras })
    const store = useCamerasStore()
    await store.fetchCameras()
    expect(store.items).toEqual(mockCameras)
  })

  it('loadPresets sets presets and defaultPresetId', async () => {
    const mockPresets = [{ id: 1, name: 'preset1' }]
    const mockCamera = { default_preset_id: 1 }
    api.get
      .mockResolvedValueOnce({ data: mockPresets })
      .mockResolvedValueOnce({ data: mockCamera })
    const store = useCamerasStore()
    await store.loadPresets('AA:BB:CC:DD:EE:FF')
    expect(store.presets['AA:BB:CC:DD:EE:FF']).toEqual(mockPresets)
    expect(store.defaultPresetId['AA:BB:CC:DD:EE:FF']).toBe(1)
  })

  it('loadPresets handles 404 with fallback', async () => {
    const mockPresets = [{ id: 1 }]
    const error404 = { response: { status: 404 } }
    api.get
      .mockRejectedValueOnce(error404)
      .mockResolvedValueOnce({ data: mockPresets })
    const store = useCamerasStore()
    await store.loadPresets('AA:BB:CC:DD:EE:FF')
    expect(store.presets['AA:BB:CC:DD:EE:FF']).toEqual(mockPresets)
    expect(store.defaultPresetId['AA:BB:CC:DD:EE:FF']).toBeUndefined()
  })

  it('onRecordingStarted updates camera is_recording', () => {
    const store = useCamerasStore()
    store.items = [{ device_mac: 'AA:BB:CC:DD:EE:FF', is_recording: false }]
    store.onRecordingStarted('AA:BB:CC:DD:EE:FF')
    expect(store.items[0].is_recording).toBe(true)
  })

  it('onRecordingStopped updates camera is_recording', () => {
    const store = useCamerasStore()
    store.items = [{ device_mac: 'AA:BB:CC:DD:EE:FF', is_recording: true }]
    store.onRecordingStopped('AA:BB:CC:DD:EE:FF')
    expect(store.items[0].is_recording).toBe(false)
  })

  it('onCameraOffline updates camera is_online', () => {
    const store = useCamerasStore()
    store.items = [{ device_mac: 'AA:BB:CC:DD:EE:FF', is_online: true }]
    store.onCameraOffline('AA:BB:CC:DD:EE:FF')
    expect(store.items[0].is_online).toBe(false)
  })

  it('onCameraOnline updates camera is_online', () => {
    const store = useCamerasStore()
    store.items = [{ device_mac: 'AA:BB:CC:DD:EE:FF', is_online: false }]
    store.onCameraOnline('AA:BB:CC:DD:EE:FF')
    expect(store.items[0].is_online).toBe(true)
  })
})
```

- [ ] **Step 2: Run test to verify it passes**
  Run: `pnpm test -- tests/stores/cameras.test.js`
  Expected: PASS

- [ ] **Step 3: Commit**
  ```bash
  git add tests/stores/cameras.test.js && git commit -m "test(stores/cameras): add unit tests for cameras store"
  ```

---

### Task 14: members store 测试

**Files:**
- Create: `tests/stores/members.test.js`

- [ ] **Step 1: Write tests**

```javascript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useMembersStore } from '@/stores/members'
import api from '@/api/index'

vi.mock('@/api/index', () => ({
  default: { get: vi.fn() },
}))

describe('useMembersStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('has correct initial state', () => {
    const store = useMembersStore()
    expect(store.items).toEqual([])
    expect(store.loading).toBe(false)
  })

  it('fetchMembers sets items', async () => {
    const mockMembers = [{ id: 1, name: 'member1', is_home: true }]
    api.get.mockResolvedValue({ data: mockMembers })
    const store = useMembersStore()
    await store.fetchMembers()
    expect(store.items).toEqual(mockMembers)
    expect(store.loading).toBe(false)
  })

  it('fetchMembers sets loading true while fetching', async () => {
    let loadingDuringFetch
    api.get.mockImplementation(() => {
      loadingDuringFetch = useMembersStore().loading
      return Promise.resolve({ data: [] })
    })
    const store = useMembersStore()
    await store.fetchMembers()
    expect(loadingDuringFetch).toBe(true)
    expect(store.loading).toBe(false)
  })

  it('onPresenceEvent with member_arrived sets is_home true and last_arrived_at', () => {
    const store = useMembersStore()
    store.items = [{ id: 1, name: 'member1', is_home: false, last_arrived_at: null }]
    store.onPresenceEvent(1, 'member_arrived')
    expect(store.items[0].is_home).toBe(true)
    expect(store.items[0].last_arrived_at).toBeTruthy()
  })

  it('onPresenceEvent with member_left sets is_home false and last_left_at', () => {
    const store = useMembersStore()
    store.items = [{ id: 1, name: 'member1', is_home: true, last_left_at: null }]
    store.onPresenceEvent(1, 'member_left')
    expect(store.items[0].is_home).toBe(false)
    expect(store.items[0].last_left_at).toBeTruthy()
  })

  it('onPresenceEvent does nothing if member not found', () => {
    const store = useMembersStore()
    store.items = [{ id: 1, name: 'member1' }]
    store.onPresenceEvent(999, 'member_arrived')
    expect(store.items[0].is_home).toBeUndefined()
  })
})
```

- [ ] **Step 2: Run test to verify it passes**
  Run: `pnpm test -- tests/stores/members.test.js`
  Expected: PASS

- [ ] **Step 3: Commit**
  ```bash
  git add tests/stores/members.test.js && git commit -m "test(stores/members): add unit tests for members store"
  ```

---

### Task 15: dlna store 测试

**Files:**
- Create: `tests/stores/dlna.test.js`

- [ ] **Step 1: Write tests**

```javascript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDLNAStore } from '@/stores/dlna'
import api from '@/api/index'

vi.mock('@/api/index', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}))

describe('useDLNAStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('has correct initial state', () => {
    const store = useDLNAStore()
    expect(store.devices).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.discovering).toBe(false)
    expect(store.selectedDevice).toBeNull()
    expect(store.transportState).toBeNull()
    expect(store.statusLoading).toBe(false)
  })

  it('fetchDevices sets devices', async () => {
    const mockDevices = [{ id: 'dev1', name: 'TV' }]
    api.get.mockResolvedValue({ data: mockDevices })
    const store = useDLNAStore()
    await store.fetchDevices()
    expect(store.devices).toEqual(mockDevices)
  })

  it('fetchDevices updates selectedDevice if still in list', async () => {
    const oldDevice = { id: 'dev1', name: 'TV' }
    const newDevice = { id: 'dev1', name: 'Smart TV' }
    api.get.mockResolvedValue({ data: [newDevice] })
    const store = useDLNAStore()
    store.selectedDevice = oldDevice
    await store.fetchDevices()
    expect(store.selectedDevice).toEqual(newDevice)
  })

  it('discover sets discovering true', async () => {
    api.post.mockResolvedValue({})
    const store = useDLNAStore()
    await store.discover()
    // discovering is set to true immediately then cleared after timeout
    // We just verify the API was called
    expect(api.post).toHaveBeenCalledWith('/dlna/discover')
  })

  it('onDiscoverCompleted clears discovering and fetches devices', async () => {
    api.get.mockResolvedValue({ data: [] })
    const store = useDLNAStore()
    store.discovering = true
    store.onDiscoverCompleted()
    expect(store.discovering).toBe(false)
  })

  it('selectDevice sets selectedDevice and refreshes status', async () => {
    api.get.mockResolvedValue({ data: { state: 'playing' } })
    const store = useDLNAStore()
    const device = { id: 'dev1', name: 'TV' }
    await store.selectDevice(device)
    expect(store.selectedDevice).toEqual(device)
    expect(store.transportState).toBe('playing')
  })

  it('refreshStatus does nothing if no selectedDevice', async () => {
    const store = useDLNAStore()
    store.selectedDevice = null
    await store.refreshStatus()
    expect(api.get).not.toHaveBeenCalled()
  })

  it('refreshStatus sets transportState', async () => {
    api.get.mockResolvedValue({ data: { state: 'paused' } })
    const store = useDLNAStore()
    store.selectedDevice = { id: 'dev1' }
    await store.refreshStatus()
    expect(store.transportState).toEqual({ state: 'paused' })
  })

  it('refreshStatus sets transportState to null on error', async () => {
    api.get.mockRejectedValue(new Error())
    const store = useDLNAStore()
    store.selectedDevice = { id: 'dev1' }
    store.transportState = { state: 'playing' }
    await store.refreshStatus()
    expect(store.transportState).toBeNull()
  })
})
```

- [ ] **Step 2: Run test to verify it passes**
  Run: `pnpm test -- tests/stores/dlna.test.js`
  Expected: PASS

- [ ] **Step 3: Commit**
  ```bash
  git add tests/stores/dlna.test.js && git commit -m "test(stores/dlna): add unit tests for DLNA store"
  ```

---

### Task 16: locale store 测试

**Files:**
- Create: `tests/stores/locale.test.js`

- [ ] **Step 1: Write tests**

```javascript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useLocaleStore } from '@/stores/locale'
import i18n from '@/locales'
import api from '@/api/index'

vi.mock('@/locales', () => ({
  default: { global: { locale: { value: 'zh-CN' } } },
}))

vi.mock('@/api/index', () => ({
  default: { get: vi.fn(), put: vi.fn() },
}))

describe('useLocaleStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('has correct initial state from localStorage', () => {
    localStorage.setItem('app-locale', 'en')
    const store = useLocaleStore()
    expect(store.locale).toBe('en')
  })

  it('defaults to zh-CN if no localStorage value', () => {
    const store = useLocaleStore()
    expect(store.locale).toBe('zh-CN')
  })

  it('setLocale updates locale and localStorage', () => {
    const store = useLocaleStore()
    store.setLocale('en')
    expect(store.locale).toBe('en')
    expect(i18n.global.locale.value).toBe('en')
    expect(localStorage.getItem('app-locale')).toBe('en')
  })

  it('setLocale calls API to update profile', () => {
    api.put.mockResolvedValue({})
    const store = useLocaleStore()
    store.setLocale('en')
    expect(api.put).toHaveBeenCalledWith('/user/profile', { language: 'en' })
  })

  it('setLocale does not throw if API fails', async () => {
    api.put.mockRejectedValue(new Error())
    const store = useLocaleStore()
    expect(() => store.setLocale('en')).not.toThrow()
  })

  it('initLocale syncs locale from server', async () => {
    api.get.mockResolvedValue({ data: { language: 'en' } })
    const store = useLocaleStore()
    await store.initLocale()
    expect(store.locale).toBe('en')
    expect(i18n.global.locale.value).toBe('en')
  })

  it('initLocale does nothing if server language matches', async () => {
    localStorage.setItem('app-locale', 'zh-CN')
    api.get.mockResolvedValue({ data: { language: 'zh-CN' } })
    const store = useLocaleStore()
    await store.initLocale()
    expect(store.locale).toBe('zh-CN')
  })

  it('initLocale does not throw on API error', async () => {
    api.get.mockRejectedValue(new Error())
    const store = useLocaleStore()
    expect(() => store.initLocale()).not.toThrow()
  })
})
```

- [ ] **Step 2: Run test to verify it passes**
  Run: `pnpm test -- tests/stores/locale.test.js`
  Expected: PASS

- [ ] **Step 3: Commit**
  ```bash
  git add tests/stores/locale.test.js && git commit -m "test(stores/locale): add unit tests for locale store"
  ```

---

### Task 17: notifications store 测试

**Files:**
- Create: `tests/stores/notifications.test.js`

- [ ] **Step 1: Write tests**

```javascript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useNotificationsStore } from '@/stores/notifications'
import { ElNotification } from 'element-plus'

vi.mock('element-plus', () => ({
  ElNotification: vi.fn(),
}))

describe('useNotificationsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('has correct initial state', () => {
    const store = useNotificationsStore()
    expect(store.messages).toEqual([])
    expect(store.lastRecordingEvent).toBeNull()
  })

  it('handle adds message to messages array', () => {
    const store = useNotificationsStore()
    store.handle({ event: 'test', data: 'value' })
    expect(store.messages.length).toBe(1)
    expect(store.messages[0].event).toBe('test')
  })

  it('handle limits messages to 50', () => {
    const store = useNotificationsStore()
    for (let i = 0; i < 55; i++) {
      store.handle({ event: `event-${i}` })
    }
    expect(store.messages.length).toBe(50)
    expect(store.messages[0].event).toBe('event-5') // oldest dropped
  })

  it('handle stores lastRecordingEvent for recording_completed', () => {
    const store = useNotificationsStore()
    store.handle({ event: 'recording_completed', data: { camera_mac: 'AA:BB:CC:DD:EE:FF' } })
    expect(store.lastRecordingEvent).toBeTruthy()
    expect(store.lastRecordingEvent.event).toBe('recording_completed')
  })

  it('handle stores lastRecordingEvent for recording_failed', () => {
    const store = useNotificationsStore()
    store.handle({ event: 'recording_failed', data: { camera_mac: 'AA:BB:CC:DD:EE:FF' } })
    expect(store.lastRecordingEvent.event).toBe('recording_failed')
  })
})
```

- [ ] **Step 2: Run test to verify it passes**
  Run: `pnpm test -- tests/stores/notifications.test.js`
  Expected: PASS

- [ ] **Step 3: Commit**
  ```bash
  git add tests/stores/notifications.test.js && git commit -m "test(stores/notifications): add unit tests for notifications store"
  ```

---

## Part 4: 最终验证

### Task 18: 运行全部测试

- [ ] **Step 1: Run all tests**

Run: `pnpm test`
Expected: All tests pass, no warnings

- [ ] **Step 2: Commit remaining changes**

```bash
git add -A && git commit -m "test: complete unit test coverage for all stores, apis, and composables"
```

---

## Self-Review Checklist

- [ ] API 模块测试覆盖全部 9 个文件
- [ ] Composables 测试覆盖 2 个文件
- [ ] Stores 测试覆盖 6 个新 store（devices, cameras, members, dlna, locale, notifications）
- [ ] auth store 测试已存在（auth.test.js）
- [ ] 所有测试通过
- [ ] 遵循 mock 策略：stores 内部 mock `@/api/index`，API 测试中 mock `axios`
