// src/locales/index.js
import { createI18n } from 'vue-i18n'

// Auto-load all module files via Vite glob import
const zhModules = import.meta.glob('./zh-CN/*.js', { eager: true, import: 'default' })
const enModules = import.meta.glob('./en/*.js', { eager: true, import: 'default' })

function buildMessages(modules) {
  const result = {}
  for (const [path, mod] of Object.entries(modules)) {
    const name = path.match(/\/([^/]+)\.js$/)[1]
    result[name] = mod
  }
  return result
}

const messages = {
  'zh-CN': buildMessages(zhModules),
  'en': buildMessages(enModules),
}

const datetimeFormats = {
  'zh-CN': {
    short: {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
      hour12: false,
    },
    date: {
      year: 'numeric', month: '2-digit', day: '2-digit',
    },
  },
  'en': {
    short: {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
      hour12: true,
    },
    date: {
      year: 'numeric', month: 'short', day: 'numeric',
    },
  },
}

const i18n = createI18n({
  legacy: false,
  locale: 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages,
  datetimeFormats,
})

export default i18n
