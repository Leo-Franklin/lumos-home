import { describe, it, expect } from 'vitest'
import { resolveDeviceLabel, buildDeviceMap } from '@/utils/memberDeviceLabel'

describe('resolveDeviceLabel', () => {
  it('returns em dash when mac is missing', () => {
    expect(resolveDeviceLabel(null, {})).toBe('—')
    expect(resolveDeviceLabel('', {})).toBe('—')
  })

  it('returns mac when device is unknown', () => {
    expect(resolveDeviceLabel('AA:BB:CC:DD:EE:FF', {})).toBe('AA:BB:CC:DD:EE:FF')
  })

  it('prefers alias over hostname', () => {
    const map = buildDeviceMap([
      { mac: 'AA:BB:CC:DD:EE:01', alias: 'Alice Phone', hostname: 'iphone' },
    ])
    expect(resolveDeviceLabel('AA:BB:CC:DD:EE:01', map)).toBe('Alice Phone')
  })

  it('falls back to device_info fields on bound device rows', () => {
    const map = {
      'BB:BB:CC:DD:EE:02': {
        mac: 'BB:BB:CC:DD:EE:02',
        device_info: { alias: 'Work Laptop', hostname: 'laptop' },
      },
    }
    expect(resolveDeviceLabel('BB:BB:CC:DD:EE:02', map)).toBe('Work Laptop')
  })
})

describe('buildDeviceMap', () => {
  it('indexes devices by mac', () => {
    const map = buildDeviceMap([
      { mac: 'AA:BB:CC:DD:EE:01', alias: 'Phone' },
      { mac: 'BB:BB:CC:DD:EE:02', hostname: 'laptop' },
    ])
    expect(Object.keys(map)).toHaveLength(2)
    expect(map['AA:BB:CC:DD:EE:01'].alias).toBe('Phone')
  })
})
