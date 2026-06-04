import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import prettier from 'eslint-config-prettier'

export default [
  js.configs.recommended,
  ...vue.configs['flat/recommended'],
  prettier,
  {
    ignores: ['dist/**', 'node_modules/**', 'coverage/**'],
  },
  {
    files: ['**/*.{js,vue}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        // Vitest
        describe: 'readonly',
        it: 'readonly',
        expect: 'readonly',
        beforeEach: 'readonly',
        afterEach: 'readonly',
        beforeAll: 'readonly',
        afterAll: 'readonly',
        vi: 'readonly',
        // Vue
        defineProps: 'readonly',
        defineEmits: 'readonly',
        defineExpose: 'readonly',
        withDefaults: 'readonly',
      },
    },
    rules: {
      // Loose starter: silence noisy stylistic rules so the lint pass
      // can gate on real bugs (no-undef, no-unused-vars, no-dupe-keys,
      // no-empty) without forcing a wide refactor of dialog props,
      // attribute order, etc. Tighten over time as the codebase is
      // refactored.
      // NOTE: vue/no-mutating-props and vue/no-v-html are intentionally
      // KEPT ENABLED — they catch real Vue 3 anti-patterns and XSS
      // vectors respectively.
      'vue/attributes-order': 'off',
      'vue/v-on-event-hyphenation': 'off',
      'vue/no-template-shadow': 'off',
      'vue/require-default-prop': 'off',
      'vue/multi-word-component-names': 'off',
    },
  },
  {
    // Node.js globals for build / config files only.
    files: ['vite.config.js', 'vitest.config.js'],
    languageOptions: {
      globals: {
        __dirname: 'readonly',
        __filename: 'readonly',
        process: 'readonly',
        console: 'readonly',
      },
    },
  },
]
