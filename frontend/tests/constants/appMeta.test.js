import { describe, it, expect } from 'vitest'
import packageJson from '../../package.json'
import {
  APP_VERSION,
  pickAppVersion,
  normalizeAppVersion,
  formatAppVersion,
} from '@/constants/appMeta'

describe('appMeta', () => {
  it('APP_VERSION matches package.json', () => {
    expect(APP_VERSION).toBe(packageJson.version)
  })

  it('pickAppVersion reads version fields from payloads', () => {
    expect(pickAppVersion({ version: '1.2.3' })).toBe('1.2.3')
    expect(pickAppVersion({ app_version: '0.2.0' })).toBe('0.2.0')
    expect(pickAppVersion({ version: '2.0.0', app_version: '1.0.0' })).toBe('2.0.0')
    expect(pickAppVersion(null)).toBe('')
  })

  it('normalizeAppVersion strips leading v', () => {
    expect(normalizeAppVersion('v0.2.0')).toBe('0.2.0')
    expect(normalizeAppVersion('0.2.0')).toBe('0.2.0')
  })

  it('formatAppVersion renders display label', () => {
    expect(formatAppVersion('0.2.0')).toBe('v0.2.0')
    expect(formatAppVersion('v0.2.0')).toBe('v0.2.0')
    expect(formatAppVersion('')).toBe('—')
  })
})
