import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { h, provide, inject } from 'vue'
import { createI18n } from 'vue-i18n'
import CameraTable from '@/components/cameras/CameraTable.vue'
import zhCameras from '@/locales/zh-CN/cameras.js'

const i18n = createI18n({
  legacy: false,
  locale: 'zh-CN',
  messages: { 'zh-CN': { cameras: zhCameras } },
})

// CameraTable is a thin wrapper over Element Plus's el-table. EP isn't
// installed in unit tests, so we stub the table/column pair to forward
// the row scope to the action-column slot, and stub the rest of the EP
// components used inside that slot so the live-preview <el-button> renders
// to a real <button> element that the tests can query and click.
const ElTableStub = {
  name: 'ElTableStub',
  props: ['data'],
  setup(props, { slots }) {
    provide('el-table-data', props.data)
    return () => h('div', { class: 'el-table-stub' }, slots.default?.())
  },
}

const ElTableColumnStub = {
  name: 'ElTableColumnStub',
  inheritAttrs: false,
  setup(_, { slots }) {
    const data = inject('el-table-data', [])
    const row = data[0] || {}
    return () =>
      h('div', { class: 'el-table-column-stub' }, slots.default?.({ row, column: {}, $index: 0 }))
  },
}

const passthroughSlot = (tag) => ({
  // PascalCase name avoids Vue's "Do not use built-in or reserved HTML elements
  // as component id" warning when the rendered tag is something like 'span'.
  name: `Stub${tag.charAt(0).toUpperCase()}${tag.slice(1)}`,
  inheritAttrs: false,
  setup(_, { slots, attrs }) {
    return () => h(tag, attrs, slots.default?.())
  },
})

// el-button is the only EP component the test actually queries, so we make
// sure it renders a real <button> with the slot text in its body.
const ElButtonStub = {
  name: 'ElButtonStub',
  inheritAttrs: false,
  setup(_, { slots, attrs }) {
    return () => h('button', attrs, slots.default?.())
  },
}

// `v-loading` is a directive on el-table; we strip it so the stubbed table
// doesn't try to resolve an unregistered directive.
const stripLoading = {
  mounted(el, binding) {
    if (binding.arg === 'loading') {
      el.removeAttribute('v-loading')
      el.removeAttribute(':loading')
      el.removeAttribute('loading')
    }
  },
}

const epStubs = {
  'el-table': ElTableStub,
  'el-table-column': ElTableColumnStub,
  'el-button': ElButtonStub,
  'el-tooltip': passthroughSlot('span'),
  'el-icon': passthroughSlot('span'),
  'el-tag': passthroughSlot('span'),
  'el-dropdown': passthroughSlot('span'),
  'el-dropdown-menu': passthroughSlot('ul'),
  'el-dropdown-item': passthroughSlot('li'),
}

const sampleCamera = {
  device_mac: 'AA:BB:CC:DD:EE:01',
  onvif_host: '192.168.1.10',
  onvif_port: 2020,
  rtsp_url: 'rtsp://192.168.1.10/stream',
  stream_profile: 'mainStream',
  is_online: true,
  is_recording: false,
  last_probe_at: null,
}

const mountTable = (cameras) =>
  mount(CameraTable, {
    props: { cameras },
    global: {
      plugins: [i18n],
      stubs: epStubs,
      directives: { loading: stripLoading },
    },
  })

describe('CameraTable', () => {
  it('shows labeled live preview button when rtsp_url is set', () => {
    const wrapper = mountTable([sampleCamera])
    expect(wrapper.text()).toContain('实时预览')
  })

  it('emits preview live when live preview is clicked', async () => {
    const wrapper = mountTable([sampleCamera])
    const liveBtn = wrapper.findAll('button').find((btn) => btn.text().includes('实时预览'))
    expect(liveBtn).toBeTruthy()
    await liveBtn.trigger('click')
    expect(wrapper.emitted('preview')).toEqual([['live', sampleCamera]])
  })

  it('disables live preview when rtsp_url is missing', () => {
    const wrapper = mountTable([{ ...sampleCamera, rtsp_url: null }])
    const liveBtn = wrapper.findAll('button').find((btn) => btn.text().includes('实时预览'))
    expect(liveBtn?.attributes('disabled')).toBeDefined()
  })
})
