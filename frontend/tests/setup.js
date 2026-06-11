// Vitest setup: silence predictable noise from tests that mount real
// components without registering Element Plus globally. These warnings are
// expected and carry no signal during the unit test run.
//
// We filter on the message prefix so real warnings (e.g. user-code template
// mistakes) still surface.
const NOISE_PATTERNS = [
  // el-button, el-icon, el-skeleton, el-switch, el-input, etc. — used as
  // native tags in our components but not globally registered in tests.
  /^\[Vue warn\]: Failed to resolve component: el-/,
  // Date formatting received `null` from a test seed that intentionally
  // leaves `last_probe_at` unpopulated.
  /^\[intlify\] Invalid argument for datetime formatting/,
  // "vi.fn() mock did not use 'function' or 'class'" — stylistic, not a bug.
  /The vi\.fn\(\) mock did not use 'function' or 'class'/,
]

const originalWarn = console.warn.bind(console)
const originalError = console.error.bind(console)

function shouldSilence(args) {
  const first = args[0]
  return typeof first === 'string' && NOISE_PATTERNS.some((re) => re.test(first))
}

console.warn = (...args) => {
  if (shouldSilence(args)) return
  originalWarn(...args)
}
console.error = (...args) => {
  if (shouldSilence(args)) return
  originalError(...args)
}
