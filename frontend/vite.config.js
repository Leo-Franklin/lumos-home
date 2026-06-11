import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// Rolldown plugin: strip two invalid `pure` annotations in @vueuse/core@14.3.0
// that Rolldown (Vite 8's bundler) refuses to interpret and warns about as
// [INVALID_ANNOTATION] on every build.
//
// Pattern A (around line 3362, in the bundled useEventBus/internal.ts region):
//   the `pure` annotation is on its own line immediately above a `const`
//   declaration. Rolldown only honors pure annotations that sit directly in
//   front of a call or `new` expression. The valid annotation sits next to
//   `new Map()` on the same line; the duplicate on the line above is the
//   noisy one.
//
// Pattern B (around line 5780, in the bundled usePointer/index.ts region):
//   the `pure` annotation is placed inside parentheses, before an object
//   literal. Object literals are not call/new expressions, so the annotation
//   has no DCE effect regardless of position.
//
// Removing both is a no-op for tree-shaking: the @vueuse/core package
// declares `sideEffects: false`, so whole modules are still dropped when
// unused, and the valid annotation on the `new Map()` line is left intact.
// See https://rolldown.rs/in-depth/dead-code-elimination#pure
//
// This is a Rolldown `load` hook plugged into `build.rolldownOptions.plugins`.
// Vite 8's `transform` plugin hook does not run for `node_modules` in
// production builds (Vite hands frozen deps to Rolldown directly), and
// Vite 8 does NOT pre-bundle deps during `vite build` (no
// `node_modules/.vite/deps/` is produced), so `optimizeDeps.rolldownOptions`
// plugins also never fire in production. The warning originates inside the
// main Rolldown bundle, so the fix has to be a Rolldown-level plugin.
import { readFile } from 'node:fs/promises'

const stripInvalidVueusePureAnnotations = {
  name: 'strip-invalid-vueuse-pure-annotations',
  async load(id) {
    // Match pnpm-hoisted paths like
    //   .../node_modules/.pnpm/@vueuse+core@14.3.0_.../@vueuse/core/dist/index.js
    // and the un-hoisted fallback
    //   .../node_modules/@vueuse/core/dist/index.js
    // Anchor on the package-name segment + the trailing dist file to avoid
    // accidentally matching anything else that happens to contain "vueuse".
    if (
      !/node_modules[\\/](?:\.pnpm[\\/])?@vueuse[+_]core(?:@[^\\/]+)?[\\/].*?[\\/]dist[\\/]index\.js$/.test(
        id,
      )
    ) {
      return null
    }
    const code = await readFile(id, 'utf-8')
    return (
      code
        // Pattern A: a `pure` comment on its own line, immediately above
        // `const events = new Map()`. Drop the comment, keep the binding.
        .replace(/\/\* #__PURE__ \*\/\nconst events = /g, 'const events = ')
        // Pattern B: `const defaultState = (` followed by a `pure` comment
        // then an object literal. Drop the comment, keep the parens.
        .replace(/const defaultState = \(\/\* #__PURE__ \*\/\s*\{/g, 'const defaultState = ({')
    )
  },
}

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': resolve(__dirname, 'src') },
  },
  base: './',
  build: {
    outDir: resolve(__dirname, '../backend/frontend'),
    emptyOutDir: true,
    // Largest legitimate chunk is the main bundle (Element Plus + Vue + d3 ≈ 1.35 MB).
    // Default 500 kB is too aggressive for this stack; 1600 kB is the
    // minimum that silences the warning without hiding real bloat.
    chunkSizeWarningLimit: 1600,
    rolldownOptions: {
      plugins: [stripInvalidVueusePureAnnotations],
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
