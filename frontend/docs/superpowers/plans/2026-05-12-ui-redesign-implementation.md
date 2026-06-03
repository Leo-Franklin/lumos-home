# Smart Home UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete UI redesign of smart home frontend with refined tech aesthetic - glass morphism effects, improved color system, better motion, and view-specific optimizations.

**Architecture:** 
- Phase 1: Design system foundation in style.css (CSS variables, animations, glass effects)
- Phase 2: Create reusable components (StatCard, ActivityFeed, FilterChip, EmptyState)
- Phase 3: Update each view to use new components and patterns
- Phase 4: Global enhancements (sidebar grouping, breadcrumb, accessibility)

**Tech Stack:** Vue 3, Element Plus, CSS Variables, CSS Animations

---

## File Structure

**Files to CREATE:**
- `src/components/StatCard.vue` - Dashboard stat card with glass effect
- `src/components/ActivityFeed.vue` - Activity feed with scroll fade
- `src/components/FilterChip.vue` - Pill-shaped filter button
- `src/components/EmptyState.vue` - Empty state with illustration

**Files to MODIFY:**
- `src/style.css` - Design system foundation
- `src/views/DashboardView.vue` - Use StatCard, ActivityFeed
- `src/views/DevicesView.vue` - Card layout, FilterChip, EmptyState
- `src/views/CameraView.vue` - Action dropdown grouping
- `src/views/RecordingsView.vue` - Filter bar redesign, action priority
- `src/layout/MainLayout.vue` - Sidebar grouping, breadcrumb
- `src/components/DeviceCard.vue` - Full card redesign

---

## Phase 1: Design System Foundation

### Task 1: Update style.css - Color Variables

**Files:**
- Modify: `src/style.css:1-163`

- [ ] **Step 1: Replace color palette section**

Locate the `:root` section in style.css (lines 9-163). Replace the color variables with:

```css
:root {
  /* Primary - Refined Purple */
  --color-primary:        #6366F1;
  --color-primary-hover:  #4F46E5;
  --color-primary-subtle: rgba(99, 102, 241, 0.12);
  --color-primary-border: rgba(99, 102, 241, 0.30);

  /* Dark Canvas - Enhanced Depth */
  --color-bg:              #0F0F12;
  --color-surface:         #18181C;
  --color-surface-raised:  #222228;
  --color-surface-overlay: #2A2A32;
  --color-border:          #32323C;
  --color-border-subtle:   #28282E;

  /* Text - Improved Contrast */
  --color-text-primary:   #F4F4F6;
  --color-text-secondary: #A0A0AB;
  --color-text-muted:     #6B6B76;
  --color-text-inverse:   #FFFFFF;

  /* Semantic Colors */
  --color-online:   #10B981;
  --color-offline:  #6B7280;
  --color-error:    #EF4444;
  --color-warning:  #F59E0B;
  --color-success:  #10B981;
  --color-scanning: #F59E0B;

  /* Device Type Colors - Keep existing but verify hex values */
  --color-type-camera:        #6366F1;
  --color-type-computer:      #10B981;
  --color-type-phone:         #F59E0B;
  --color-type-iot:           #F97316;
  --color-type-unknown:       #6B7280;
  --color-type-router:        #06B6D4;
  --color-type-tablet:        #D946EF;
  --color-type-tv:            #8B5CF6;
  --color-type-printer:       #14B8A6;
  --color-type-smart-speaker: #84CC16;
  --color-type-game-console:  #EF4444;
  --color-type-nas:           #3B82F6;
  --color-type-wearable:      #EC4899;

  /* Activity Feed Colors */
  --color-cat-device:   #3B82F6;
  --color-cat-camera:   #10B981;
  --color-cat-member:   #6366F1;
  --color-cat-system:   #6B7280;

  /* Accent Colors */
  --color-accent-members:     #6366F1;
  --color-accent-cameras:     #10B981;
  --color-accent-devices:     #3B82F6;
  --color-accent-recordings:  #F59E0B;
  --color-accent-unknown:     #6B7280;
  --color-accent-unknown-warn:#F59E0B;

  /* Warm Tones */
  --color-warm-peach:   #E8A87C;
  --color-warm-coral:   #F08080;
  --color-warm-amber:   #E8B86D;

  /* Border Radius */
  --radius-xs:   3px;
  --radius-sm:   4px;
  --radius-md:   6px;
  --radius-lg:   8px;
  --radius-xl:   12px;
  --radius-full: 9999px;

  /* Shadows */
  --shadow-sm:    0 1px 4px rgba(0, 0, 0, 0.5);
  --shadow-md:    0 4px 12px rgba(0, 0, 0, 0.6);
  --shadow-lg:    0 8px 24px rgba(0, 0, 0, 0.7);
  --shadow-focus: 0 0 0 2px rgba(99, 102, 241, 0.4);

  /* Motion */
  --duration-fast:   100ms;
  --duration-base:   200ms;
  --duration-slow:   300ms;
  --duration-slower: 400ms;
  --easing-standard: cubic-bezier(0.4, 0, 0.2, 1);
  --easing-snap:    cubic-bezier(0.16, 1, 0.3, 1);
  --easing-spring:  cubic-bezier(0.34, 1.56, 0.64, 1);

  /* Spacing */
  --space-1:  4px;
  --space-2:  8px;
  --space-3:  12px;
  --space-4:  16px;
  --space-5:  20px;
  --space-6:  24px;
  --space-8:  32px;
  --space-10: 40px;

  /* Layout */
  --sidebar-width:           220px;
  --sidebar-width-collapsed: 48px;
  --header-height:           56px;
  --content-max-width:       1400px;

  /* Typography */
  --font-display: "Outfit", -apple-system, BlinkMacSystemFont, sans-serif;
  --font-sans: "Noto Sans SC", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  --font-mono: "JetBrains Mono", "Fira Code", Consolas, monospace;
  --font-tabular: "Outfit", monospace;

  /* Element Plus Overrides - keep existing but verify values */
  --el-color-primary:              var(--color-primary);
  --el-color-primary-light-3:     rgba(99, 102, 241, 0.7);
  --el-color-primary-light-5:     rgba(99, 102, 241, 0.5);
  --el-color-primary-light-7:     rgba(99, 102, 241, 0.3);
  --el-color-primary-light-8:     rgba(99, 102, 241, 0.2);
  --el-color-primary-light-9:     rgba(99, 102, 241, 0.1);
  --el-color-primary-dark-2:      var(--color-primary-hover);

  --el-bg-color:                  var(--color-surface);
  --el-bg-color-page:             var(--color-bg);
  --el-bg-color-overlay:          var(--color-surface-overlay);

  --el-text-color-primary:        var(--color-text-primary);
  --el-text-color-regular:        var(--color-text-secondary);
  --el-text-color-secondary:      var(--color-text-muted);
  --el-text-color-disabled:       var(--color-text-muted);
  --el-text-color-placeholder:    var(--color-text-muted);

  --el-border-color:              var(--color-border);
  --el-border-color-light:        var(--color-border);
  --el-border-color-lighter:      var(--color-border-subtle);
  --el-border-color-extra-light:  var(--color-border-subtle);
  --el-border-color-dark:         var(--color-border);
  --el-border-color-darker:       var(--color-border);

  --el-fill-color:                var(--color-surface-raised);
  --el-fill-color-light:          var(--color-surface-raised);
  --el-fill-color-lighter:        var(--color-surface);
  --el-fill-color-extra-light:    var(--color-surface);
  --el-fill-color-dark:           var(--color-surface-overlay);
  --el-fill-color-darker:         var(--color-surface-overlay);
  --el-fill-color-blank:          var(--color-surface);

  --el-box-shadow:                var(--shadow-md);
  --el-box-shadow-light:          var(--shadow-sm);
  --el-box-shadow-lighter:        var(--shadow-sm);
  --el-box-shadow-dark:           var(--shadow-lg);

  --el-mask-color:                rgba(0, 0, 0, 0.6);
  --el-overlay-color:             rgba(0, 0, 0, 0.6);

  --el-border-radius-base:         var(--radius-md);
  --el-border-radius-small:        var(--radius-xs);
  --el-border-radius-round:        var(--radius-full);
  --el-border-radius-circle:       var(--radius-full);

  --el-font-size-base:            14px;
  --el-font-size-small:           12px;
  --el-font-size-extra-small:     11px;

  --el-transition-duration:        var(--duration-base);
  --el-transition-duration-fast:   var(--duration-fast);

  --el-component-size:            32px;
  --el-component-size-small:      24px;
  --el-component-size-large:      40px;

  --el-disabled-bg-color:          var(--color-surface);
  --el-disabled-text-color:        var(--color-text-muted);
  --el-disabled-border-color:      var(--color-border-subtle);
}
```

- [ ] **Step 2: Update body font to use display font for numbers**

Replace html, body section:

```css
html, body {
  font-family: var(--font-sans);
  background: var(--color-bg);
  color: var(--color-text-primary);
  font-size: 14px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Use display font for large numbers */
.tabular-nums,
.stat-value {
  font-family: var(--font-display);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.03em;
}
```

- [ ] **Step 3: Update animations section**

Replace the animation keyframes:

```css
/* Page transitions */
.page-enter-active {
  transition: opacity var(--duration-base) var(--easing-standard),
              transform var(--duration-base) var(--easing-snap);
}
.page-leave-active {
  transition: opacity var(--duration-fast) var(--easing-standard);
}
.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-leave-to {
  opacity: 0;
}

/* Stagger animation for lists */
@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fade-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}

/* WebSocket pulse - more visible */
@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.5); }
  50%       { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
}

/* Recording indicator pulse */
@keyframes recording-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.5; }
}
```

- [ ] **Step 4: Add glass card utility class**

Add after the WebSocket pulse animation:

```css
/* Glass card utility */
.glass-card {
  background: rgba(24, 24, 28, 0.8);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-xl);
}

/* Glow border utility */
.glow-border {
  position: relative;
}
.glow-border::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: inherit;
  background: linear-gradient(135deg, var(--color-primary), transparent 50%);
  opacity: 0.4;
  z-index: -1;
  transition: opacity var(--duration-base) var(--easing-standard);
}
.glow-border:hover::before {
  opacity: 0.6;
}
```

- [ ] **Step 5: Commit Phase 1**

```bash
git add src/style.css
git commit -m "feat(ui): update design system foundation - colors, spacing, animations, glass effects"
```

---

## Phase 2: Core Components

### Task 2: Create StatCard Component

**Files:**
- Create: `src/components/StatCard.vue`

- [ ] **Step 1: Create StatCard.vue**

```vue
<script setup>
defineProps({
  title: { type: String, required: true },
  value: { type: [String, Number], required: true },
  total: { type: [String, Number], default: null },
  suffix: { type: String, default: '' },
  description: { type: String, default: '' },
  trend: { type: String, default: null },  // e.g., "+2 vs last week"
  icon: { type: Object, default: null },
  iconColor: { type: String, default: 'var(--color-primary)' },
  variant: { 
    type: String, 
    default: 'default',
    validator: (v) => ['default', 'members', 'cameras', 'devices', 'recordings', 'unknown'].includes(v)
  },
  warning: { type: Boolean, default: false },
})
</script>

<template>
  <div 
    class="stat-card glass-card"
    :class="[`stat-card--${variant}`, { 'stat-card--warn': warning }]"
  >
    <div class="stat-icon-wrap">
      <div class="stat-icon" :style="{ color: iconColor }">
        <slot name="icon">
          <svg v-if="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <component :is="icon" />
          </svg>
        </slot>
      </div>
    </div>
    <div class="stat-body">
      <div class="stat-header">{{ title }}</div>
      <div class="stat-value-row">
        <span class="stat-value">{{ value }}</span>
        <span v-if="total !== null" class="stat-total">/ {{ total }}</span>
        <span v-if="suffix" class="stat-suffix">{{ suffix }}</span>
      </div>
      <div class="stat-desc-row">
        <span class="stat-desc">{{ description }}</span>
        <span v-if="trend" class="stat-trend">{{ trend }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stat-card {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  padding: var(--space-5);
  transition: transform var(--duration-base) var(--easing-snap),
              box-shadow var(--duration-base) var(--easing-standard);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.stat-card--warn {
  border-color: rgba(245, 158, 11, 0.3);
  background: rgba(245, 158, 11, 0.06);
}

.stat-icon-wrap {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-raised);
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.2);
}

.stat-icon {
  width: 22px;
  height: 22px;
}

.stat-icon :deep(svg) {
  width: 100%;
  height: 100%;
}

.stat-body {
  flex: 1;
  min-width: 0;
}

.stat-header {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: var(--space-2);
}

.stat-value-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-1);
  margin-bottom: var(--space-1);
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
}

.stat-total {
  font-size: 18px;
  font-weight: 400;
  color: var(--color-text-muted);
}

.stat-suffix {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-left: var(--space-1);
}

.stat-desc-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.stat-desc {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.stat-trend {
  font-size: 11px;
  color: var(--color-success);
  font-weight: 500;
}

/* Variant colors for icon backgrounds */
.stat-card--members .stat-icon-wrap { background: rgba(99, 102, 241, 0.12); }
.stat-card--cameras .stat-icon-wrap { background: rgba(16, 185, 129, 0.12); }
.stat-card--devices .stat-icon-wrap { background: rgba(59, 130, 246, 0.12); }
.stat-card--recordings .stat-icon-wrap { background: rgba(245, 158, 11, 0.12); }
.stat-card--unknown .stat-icon-wrap { background: rgba(107, 114, 128, 0.12); }
.stat-card--warn .stat-icon-wrap { background: rgba(245, 158, 11, 0.15); }

/* Animation */
.stat-card {
  animation: fade-up var(--duration-base) var(--easing-snap) both;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add src/components/StatCard.vue
git commit -m "feat(ui): add StatCard component with glass effect"
```

---

### Task 3: Create ActivityFeed Component

**Files:**
- Create: `src/components/ActivityFeed.vue`

- [ ] **Step 1: Create ActivityFeed.vue**

```vue
<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  items: { type: Array, default: () => [] },
  maxHeight: { type: Number, default: 420 },
  showViewAll: { type: Boolean, default: false },
})

const emit = defineEmits(['viewAll'])

const EVENT_COLORS = {
  device: 'var(--color-cat-device)',
  camera: 'var(--color-cat-camera)',
  member: 'var(--color-cat-member)',
  system: 'var(--color-cat-system)',
}

function getDotColor(category) {
  return EVENT_COLORS[category] || EVENT_COLORS.system
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  
  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}小时前`
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}
</script>

<template>
  <div class="activity-panel glass-card">
    <div class="activity-header">
      <span class="activity-title">{{ $t('dashboard.recentActivity') }}</span>
      <el-button 
        v-if="showViewAll" 
        link 
        size="small" 
        class="view-all-btn"
        @click="emit('viewAll')"
      >
        {{ $t('common.viewAll') }}
      </el-button>
    </div>
    
    <div class="activity-list" :style="{ maxHeight: maxHeight + 'px' }">
      <div v-if="items.length === 0" class="activity-empty">
        <span>{{ $t('dashboard.noRecentActivity') }}</span>
      </div>
      <div
        v-else
        v-for="(item, index) in items"
        :key="index"
        class="activity-item"
        :style="{ animationDelay: Math.min(index * 30, 200) + 'ms' }"
      >
        <span 
          class="activity-dot" 
          :style="{ background: getDotColor(item.category) }"
        />
        <span class="activity-label">{{ item.label }}</span>
        <span v-if="item.timestamp" class="activity-time">
          {{ formatTime(item.timestamp) }}
        </span>
      </div>
    </div>
    
    <div v-if="items.length > 0" class="activity-fade" />
  </div>
</template>

<style scoped>
.activity-panel {
  padding: var(--space-5);
  max-height: v-bind('maxHeight + 60 + "px"');
  display: flex;
  flex-direction: column;
}

.activity-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
  flex-shrink: 0;
}

.activity-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.view-all-btn {
  font-size: 12px;
  color: var(--color-primary);
}

.activity-list {
  overflow-y: auto;
  flex: 1;
  position: relative;
  padding-right: var(--space-2);
}

.activity-list::-webkit-scrollbar {
  width: 4px;
}

.activity-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-full);
}

.activity-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  font-size: 13px;
  color: var(--color-text-primary);
  animation: fade-up var(--duration-base) var(--easing-snap) both;
}

.activity-item + .activity-item {
  border-top: 1px solid var(--color-border-subtle);
}

.activity-dot {
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.activity-label {
  flex: 1;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-time {
  font-size: 11px;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.activity-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  font-size: 13px;
  padding: var(--space-8) 0;
}

.activity-fade {
  position: absolute;
  bottom: 0;
  left: 0;
  right: var(--space-2);
  height: 40px;
  background: linear-gradient(to top, rgba(24, 24, 28, 0.9), transparent);
  pointer-events: none;
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add src/components/ActivityFeed.vue
git commit -m "feat(ui): add ActivityFeed component with scroll fade"
```

---

### Task 4: Create FilterChip Component

**Files:**
- Create: `src/components/FilterChip.vue`

- [ ] **Step 1: Create FilterChip.vue**

```vue
<script setup>
defineProps({
  label: { type: String, required: true },
  active: { type: Boolean, default: false },
  color: { type: String, default: null },  // hex or CSS var
  count: { type: Number, default: null },
})

defineEmits(['click'])
</script>

<template>
  <button 
    class="filter-chip"
    :class="{ active }"
    :style="active && color ? { 
      '--chip-color': color,
      '--chip-bg': color + '18',
      '--chip-border': color + '50'
    } : {}"
    @click="$emit('click')"
  >
    <span 
      v-if="color" 
      class="chip-dot" 
      :style="{ background: active ? 'var(--chip-color)' : color }"
    />
    <span class="chip-label">{{ label }}</span>
    <span v-if="count !== null" class="chip-count">{{ count }}</span>
  </button>
</template>

<style scoped>
.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all var(--duration-fast) var(--easing-standard);
  white-space: nowrap;
}

.filter-chip:hover:not(.active) {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
}

.filter-chip.active {
  background: var(--chip-bg, var(--color-primary-subtle));
  border-color: var(--chip-border, var(--color-primary-border));
  color: var(--chip-color, var(--color-primary));
  font-weight: 500;
}

.chip-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.chip-label {
  line-height: 1;
}

.chip-count {
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  opacity: 0.7;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add src/components/FilterChip.vue
git commit -m "feat(ui): add FilterChip component with pill design"
```

---

### Task 5: Create EmptyState Component

**Files:**
- Create: `src/components/EmptyState.vue`

- [ ] **Step 1: Create EmptyState.vue**

```vue
<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  icon: { type: String, default: 'device' },  // 'device' | 'camera' | 'recording' | 'search'
  actionLabel: { type: String, default: null },
})

defineEmits(['action'])
</script>

<template>
  <div class="empty-state">
    <div class="empty-illustration">
      <!-- Device illustration -->
      <svg v-if="icon === 'device'" viewBox="0 0 120 80" fill="none">
        <rect x="30" y="20" width="60" height="40" rx="6" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
        <rect x="50" y="55" width="20" height="5" rx="2" fill="var(--color-surface-raised)"/>
        <circle cx="60" cy="40" r="10" fill="var(--color-text-muted)" opacity="0.2"/>
        <circle cx="60" cy="40" r="4" fill="var(--color-text-muted)" opacity="0.4"/>
        <circle cx="85" cy="25" r="12" fill="var(--color-surface-raised)" stroke="var(--color-warning)" stroke-width="1.5" stroke-dasharray="3 2"/>
        <path d="M85 19v12M79 25h12" stroke="var(--color-warning)" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      
      <!-- Camera illustration -->
      <svg v-else-if="icon === 'camera'" viewBox="0 0 120 80" fill="none">
        <rect x="25" y="25" width="70" height="40" rx="6" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
        <path d="M60 25v-6a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v6" stroke="var(--color-border)" stroke-width="1.5"/>
        <circle cx="60" cy="45" r="12" fill="var(--color-text-muted)" opacity="0.15"/>
        <circle cx="60" cy="45" r="6" fill="var(--color-text-muted)" opacity="0.3"/>
      </svg>
      
      <!-- Recording illustration -->
      <svg v-else-if="icon === 'recording'" viewBox="0 0 120 80" fill="none">
        <circle cx="60" cy="40" r="25" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
        <polygon points="52,32 52,48 68,40" fill="var(--color-text-muted)" opacity="0.4"/>
      </svg>
      
      <!-- Search illustration -->
      <svg v-else viewBox="0 0 120 80" fill="none">
        <circle cx="50" cy="35" r="18" fill="var(--color-surface-raised)" stroke="var(--color-border)" stroke-width="1.5"/>
        <path d="M63 48l20 20" stroke="var(--color-border)" stroke-width="3" stroke-linecap="round"/>
        <path d="M44 35h12M50 29v12" stroke="var(--color-text-muted)" stroke-width="1.5" stroke-linecap="round" opacity="0.5"/>
      </svg>
    </div>
    
    <h3 class="empty-title">{{ title }}</h3>
    <p v-if="description" class="empty-description">{{ description }}</p>
    
    <el-button 
      v-if="actionLabel" 
      type="primary" 
      class="empty-action"
      @click="$emit('action')"
    >
      {{ actionLabel }}
    </el-button>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-12) var(--space-6);
  text-align: center;
}

.empty-illustration {
  width: 120px;
  height: 80px;
  margin-bottom: var(--space-6);
  opacity: 0.8;
}

.empty-illustration svg {
  width: 100%;
  height: 100%;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2);
}

.empty-description {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-6);
  max-width: 300px;
  line-height: 1.6;
}

.empty-action {
  margin-top: var(--space-2);
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add src/components/EmptyState.vue
git commit -m "feat(ui): add EmptyState component with illustrations"
```

---

### Task 6: Update DeviceCard Component

**Files:**
- Modify: `src/components/DeviceCard.vue`

- [ ] **Step 1: Read current DeviceCard.vue**

Read the existing file to understand current structure.

- [ ] **Step 2: Replace DeviceCard with full card redesign**

Replace the entire `<style scoped>` section and update template to:

```vue
<template>
  <div class="device-card glass-card" :class="{ 'device-card--offline': !device.is_online }">
    <div class="card-header">
      <span class="status-indicator" :class="device.is_online ? 'online' : 'offline'" />
      <div class="type-badge" :style="typeIconStyle(device.device_type)">
        <el-icon :size="14">
          <component :is="typeIcon(device.device_type)" />
        </el-icon>
      </div>
    </div>
    
    <div class="card-body">
      <h3 class="device-name">{{ device.alias || device.hostname || $t('devices.unnamed') }}</h3>
      <p class="device-vendor" v-if="device.vendor">{{ device.vendor }}</p>
      
      <div class="device-meta">
        <div class="meta-item">
          <span class="meta-label">IP</span>
          <span class="meta-value mono">{{ device.ip || '—' }}</span>
        </div>
        <div class="meta-item" v-if="device.last_seen">
          <span class="meta-label">{{ $t('devices.lastSeen') }}</span>
          <span class="meta-value">{{ formatLastSeen(device.last_seen) }}</span>
        </div>
      </div>
    </div>
    
    <div class="card-footer">
      <span class="type-badge-pill" :style="typeBadgeStyle(device.device_type)">
        {{ $t(`common.deviceTypes.${device.device_type}`) }}
      </span>
    </div>
    
    <div class="card-actions">
      <el-button size="small" @click="$emit('detail', device)">{{ $t('common.detail') }}</el-button>
      <el-button size="small" @click="$emit('edit', device)">{{ $t('common.edit') }}</el-button>
      <el-button size="small" type="danger" @click="$emit('delete', device)">{{ $t('common.delete') }}</el-button>
    </div>
  </div>
</template>
```

And replace `<style scoped>` with:

```css
<style scoped>
.device-card {
  display: flex;
  flex-direction: column;
  padding: var(--space-5);
  gap: var(--space-4);
  transition: transform var(--duration-base) var(--easing-snap),
              box-shadow var(--duration-base) var(--easing-standard);
}

.device-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.device-card--offline {
  opacity: 0.7;
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-indicator.online {
  background: var(--color-online);
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
  animation: pulse-glow 2s ease-in-out infinite;
}

.status-indicator.offline {
  background: var(--color-offline);
}

.type-badge {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-body {
  flex: 1;
}

.device-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1);
  letter-spacing: -0.01em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.device-vendor {
  font-size: 12px;
  color: var(--color-text-muted);
  margin: 0 0 var(--space-3);
  font-family: var(--font-mono);
}

.device-meta {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.meta-label {
  font-size: 11px;
  color: var(--color-text-muted);
  min-width: 50px;
}

.meta-value {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.meta-value.mono {
  font-family: var(--font-mono);
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.type-badge-pill {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  letter-spacing: 0.01em;
}

.card-actions {
  display: flex;
  gap: var(--space-2);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border-subtle);
}

.card-actions .el-button {
  flex: 1;
  font-size: 12px;
}
</style>
```

Add the typeIcon function to the script section:

```javascript
// Add to script setup section
import {
  VideoCameraFilled, Monitor, Iphone, Cpu, QuestionFilled,
  Connection, Grid, Film, Printer, Microphone, Trophy, Box, Watch,
} from '@element-plus/icons-vue'

function typeIcon(t) {
  const icons = {
    camera: VideoCameraFilled,
    computer: Monitor,
    phone: Iphone,
    iot: Cpu,
    router: Connection,
    tablet: Grid,
    tv: Film,
    printer: Printer,
    smart_speaker: Microphone,
    game_console: Trophy,
    nas: Box,
    wearable: Watch,
  }
  return icons[t] || QuestionFilled
}

function formatLastSeen(timestamp) {
  if (!timestamp) return '—'
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  
  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}小时前`
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}
```

- [ ] **Step 3: Commit**

```bash
git add src/components/DeviceCard.vue
git commit -m "refactor(ui): redesign DeviceCard as full card with glass effect"
```

---

## Phase 3: View Redesigns

### Task 7: Update DashboardView

**Files:**
- Modify: `src/views/DashboardView.vue`

- [ ] **Step 1: Read current DashboardView.vue**

Read the existing file to understand current structure.

- [ ] **Step 2: Update script setup to use new components**

Add imports:
```javascript
import StatCard from '@/components/StatCard.vue'
import ActivityFeed from '@/components/ActivityFeed.vue'
```

- [ ] **Step 3: Replace stats-grid with StatCard components**

Replace `<div class="stats-grid">...</div>` section:

```vue
<div class="stats-grid">
  <StatCard
    :title="$t('dashboard.membersHome')"
    :value="data.members_home"
    :total="data.members_total"
    :description="$t('dashboard.membersHomeDesc')"
    variant="members"
    icon="members"
    :style="{ animationDelay: '0ms' }"
  >
    <template #icon>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
        <circle cx="9" cy="7" r="4"/>
        <path d="M3 21v-2a7 7 0 0 1 10-5.5"/>
        <circle cx="17" cy="8" r="3"/>
        <path d="M14 21v-2a5 5 0 0 1 3.5-4.8"/>
      </svg>
    </template>
  </StatCard>

  <StatCard
    :title="$t('dashboard.cameras')"
    :value="data.cameras_online"
    :total="data.cameras_total"
    :description="$t('dashboard.camerasOnline')"
    variant="cameras"
    icon="cameras"
    :style="{ animationDelay: '40ms' }"
  >
    <template #icon>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
        <path d="M2 8.5A2.5 2.5 0 0 1 4.5 6h9A2.5 2.5 0 0 1 16 8.5v7a2.5 2.5 0 0 1-2.5 2.5h-9A2.5 2.5 0 0 1 2 15.5v-7Z"/>
        <path d="m17 10 4.5-3v10L17 14"/>
      </svg>
    </template>
    <template #suffix>
      <span v-if="data.cameras_recording > 0" class="tag-recording">
        · {{ data.cameras_recording }}{{ $t('dashboard.camerasRecording') }}
      </span>
    </template>
  </StatCard>

  <StatCard
    :title="$t('dashboard.networkDevices')"
    :value="data.devices_online"
    :total="data.devices_total"
    :description="$t('dashboard.devicesOnline')"
    variant="devices"
    icon="devices"
    :style="{ animationDelay: '80ms' }"
  >
    <template #icon>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
        <rect x="2" y="3" width="20" height="12" rx="2"/>
        <path d="M8 21h8"/>
        <path d="M12 15v6"/>
      </svg>
    </template>
  </StatCard>

  <StatCard
    :title="$t('dashboard.todayRecordings')"
    :value="data.recordings_today_count"
    :description="$t('common.unit_record') + ' · ' + formatDuration(data.recordings_today_duration_seconds)"
    variant="recordings"
    icon="recordings"
    :style="{ animationDelay: '120ms' }"
  >
    <template #icon>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
        <circle cx="12" cy="12" r="10"/>
        <polygon points="10 8 16 12 10 16 10 8" fill="currentColor" stroke="none" opacity=".85"/>
      </svg>
    </template>
  </StatCard>

  <StatCard
    :title="$t('dashboard.unknownDevices')"
    :value="data.unknown_devices_today"
    :description="$t('dashboard.todayAppeared')"
    variant="unknown"
    :warning="data.unknown_devices_today > 0"
    icon="unknown"
    :style="{ animationDelay: '160ms' }"
  >
    <template #icon>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 16v-4"/>
        <circle cx="12" cy="8" r=".5" fill="currentColor"/>
      </svg>
    </template>
  </StatCard>
</div>
```

- [ ] **Step 4: Replace activity-panel with ActivityFeed**

Replace `<div class="activity-panel">...</div>` section:

```vue
<ActivityFeed
  :items="recentEvents"
  :max-height="420"
  :show-view-all="true"
  @view-all="navigateToActivity"
/>
```

Add navigateToActivity function:
```javascript
import { useRouter } from 'vue-router'
const router = useRouter()

function navigateToActivity() {
  router.push('/activity')  // or wherever activity history lives
}
```

- [ ] **Step 5: Add stats-grid styles**

Replace `.stats-grid` CSS section:
```css
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.tag-recording {
  color: var(--color-error);
  font-weight: 600;
}
```

Remove old `.stat-card`, `.stat-icon`, `.stat-body`, etc. CSS classes since they're now in StatCard component.

- [ ] **Step 6: Commit**

```bash
git add src/views/DashboardView.vue
git commit -m "refactor(ui): use StatCard and ActivityFeed components in Dashboard"
```

---

### Task 8: Update DevicesView

**Files:**
- Modify: `src/views/DevicesView.vue`

- [ ] **Step 1: Read current DevicesView.vue**

Read the existing file to understand current structure.

- [ ] **Step 2: Add imports for new components**

```javascript
import FilterChip from '@/components/FilterChip.vue'
import EmptyState from '@/components/EmptyState.vue'
import { useRouter } from 'vue-router'

const router = useRouter()
```

- [ ] **Step 3: Replace device-list with grid layout**

Replace `<div class="device-list">...</div>` section:

```vue
<div v-if="devicesStore.loading" class="device-grid">
  <div v-for="i in 6" :key="i" class="device-skeleton glass-card" />
</div>

<div v-else-if="devicesStore.items.length === 0" class="empty-container">
  <EmptyState
    :title="$t('devices.noDevices')"
    :description="$t('devices.noDevicesHint')"
    icon="device"
    :action-label="$t('devices.scan')"
    @action="devicesStore.scan()"
  />
</div>

<div v-else class="device-grid">
  <DeviceCard
    v-for="device in devicesStore.items"
    :key="device.mac"
    :device="device"
    @detail="openDetail"
    @edit="openEdit"
    @delete="handleDelete"
  />
</div>
```

- [ ] **Step 4: Replace filter-bar with FilterChip**

Replace `<div class="filter-bar">...</div>` section:

```vue
<div class="filter-bar">
  <el-input
    v-model="searchInput"
    :placeholder="$t('devices.searchPlaceholder')"
    clearable
    class="search-input"
    :prefix-icon="Search"
    @input="devicesStore.setSearch(searchInput)"
  />
  
  <div class="filter-chips">
    <FilterChip
      :label="$t('common.all')"
      :active="devicesStore.filterTypes.length === 0"
      @click="onAllClick"
    />
    <FilterChip
      v-for="opt in filterOptions"
      :key="opt.value"
      :label="$t(`common.deviceTypes.${opt.value}`)"
      :active="devicesStore.filterTypes.includes(opt.value)"
      :color="opt.hex"
      @click="devicesStore.toggleFilter(opt.value)"
    />
  </div>
</div>
```

Add Search icon import:
```javascript
import { Refresh, Search } from '@element-plus/icons-vue'
```

- [ ] **Step 5: Add CSS for new layout**

Replace the style section:

```css
<style scoped>
/* Filter bar */
.filter-bar {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.search-input {
  width: 280px;
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

/* Device grid */
.device-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-4);
}

.device-skeleton {
  height: 200px;
  animation: shimmer 1.4s ease infinite;
  background: linear-gradient(
    90deg,
    var(--color-surface-raised) 25%,
    var(--color-surface-overlay) 37%,
    var(--color-surface-raised) 63%
  );
  background-size: 400% 100%;
}

@keyframes shimmer {
  0%   { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.empty-container {
  display: flex;
  justify-content: center;
  padding: var(--space-12) 0;
}

/* Keep existing detail-* styles if needed for dialog */
</style>
```

Remove old `.device-list`, `.filter-btn`, `.filter-btn--clear` CSS classes.

- [ ] **Step 6: Commit**

```bash
git add src/views/DevicesView.vue
git commit -m "refactor(ui): use FilterChip and grid layout in DevicesView"
```

---

### Task 9: Update CameraView

**Files:**
- Modify: `src/views/CameraView.vue`

- [ ] **Step 1: Read current CameraView.vue**

Read the existing file.

- [ ] **Step 2: Create ActionDropdown for preview button**

Add this component inline or create separate component. For simplicity, modify the table column:

Replace the action buttons template section with dropdown grouping:

```vue
<el-table-column :label="$t('cameras.actions')" min-width="200" align="center">
  <template #default="{ row }">
    <div class="action-group">
      <!-- Probe -->
      <el-tooltip :content="$t('cameras.onvifProbe')" :show-after="400">
        <el-button class="action-btn" size="small" :icon="Search" @click="handleProbe(row)" />
      </el-tooltip>
      
      <!-- Preview dropdown -->
      <el-dropdown trigger="click" @command="(cmd) => handlePreviewCommand(cmd, row)">
        <el-button class="action-btn action-btn--primary" size="small">
          <VideoPlay />
          <el-icon class="el-icon--right"><ArrowDown /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="live">
              <el-icon><VideoPlay /></el-icon>
              {{ $t('cameras.livePreview') }}
            </el-dropdown-item>
            <el-dropdown-item command="snapshot">
              <el-icon><Camera /></el-icon>
              {{ $t('cameras.snapshot') }}
            </el-dropdown-item>
            <el-dropdown-item command="hls">
              <el-icon><VideoCamera /></el-icon>
              {{ $t('cameras.hlsLive') }}
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      
      <!-- Edit -->
      <el-tooltip :content="$t('cameras.edit')" :show-after="400">
        <el-button class="action-btn" size="small" :icon="Edit" @click="openEdit(row)" />
      </el-tooltip>
      
      <!-- Record -->
      <el-tooltip :content="row.is_recording ? $t('cameras.stopRecord') : $t('cameras.startRecord')" :show-after="400">
        <el-button
          class="action-btn"
          :class="row.is_recording ? 'action-btn--recording' : 'action-btn--record'"
          size="small"
          :icon="row.is_recording ? VideoPause : VideoCameraFilled"
          @click="handleRecord(row)"
        />
      </el-tooltip>
      
      <!-- Delete -->
      <el-tooltip :content="$t('cameras.delete')" :show-after="400">
        <el-button class="action-btn action-btn--danger" size="small" :icon="Delete" @click="handleDelete(row)" />
      </el-tooltip>
    </div>
  </template>
</el-table-column>
```

Add handlePreviewCommand function:

```javascript
import { ArrowDown } from '@element-plus/icons-vue'

function handlePreviewCommand(cmd, row) {
  switch (cmd) {
    case 'live':
      openLive(row)
      break
    case 'snapshot':
      handleSnapshot(row)
      break
    case 'hls':
      openHlsLive(row)
      break
  }
}
```

- [ ] **Step 3: Update action-btn styles**

Replace action button CSS:

```css
.action-group {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
}

.action-btn {
  --el-button-bg-color: transparent;
  --el-button-border-color: transparent;
  --el-button-hover-bg-color: var(--color-surface-raised);
  --el-button-hover-border-color: transparent;
  --el-button-hover-text-color: var(--color-text-primary);
  --el-button-active-bg-color: var(--color-surface-overlay);
  --el-button-active-border-color: transparent;
  height: 28px;
  width: 28px;
  padding: 3px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  transition: background var(--duration-fast) var(--easing-standard),
              color var(--duration-fast) var(--easing-standard);
}

.action-btn--primary {
  width: auto;
  padding: 0 var(--space-3);
  gap: var(--space-1);
}

.action-btn--primary:hover {
  background: var(--color-primary-subtle);
  color: var(--color-primary);
}

.action-btn--record {
  --el-button-hover-bg-color: rgba(16, 185, 129, 0.1);
  --el-button-hover-text-color: var(--color-online);
}

.action-btn--recording {
  --el-button-hover-bg-color: rgba(239, 68, 68, 0.1);
  --el-button-hover-text-color: var(--color-error);
  animation: recording-pulse 1.5s ease-in-out infinite;
}

.action-btn--danger {
  --el-button-hover-bg-color: rgba(239, 68, 68, 0.1);
  --el-button-hover-text-color: var(--color-error);
}

/* Dropdown menu styles */
:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 13px;
}
```

- [ ] **Step 4: Commit**

```bash
git add src/views/CameraView.vue
git commit -m "refactor(ui): group preview actions in dropdown in CameraView"
```

---

### Task 10: Update RecordingsView

**Files:**
- Modify: `src/views/RecordingsView.vue`

- [ ] **Step 1: Read current RecordingsView.vue**

Read the existing file.

- [ ] **Step 2: Replace filter bar with new layout**

Replace the el-form:inline section:

```vue
<div class="filter-section">
  <div class="filter-row">
    <el-select
      v-model="filter.camera_mac"
      :placeholder="$t('recordings.all')"
      clearable
      style="width: 200px"
    >
      <el-option
        v-for="c in cameras"
        :key="c.device_mac"
        :label="c.onvif_host"
        :value="c.device_mac"
      />
    </el-select>
    
    <el-date-picker
      v-model="filter.date"
      type="date"
      value-format="YYYY-MM-DD"
      :placeholder="$t('recordings.allDates')"
      clearable
    />
    
    <el-button type="primary" @click="fetchRecordings">
      {{ $t('recordings.query') }}
    </el-button>
  </div>
  
  <div class="filter-summary" v-if="total > 0">
    <span class="summary-count">{{ $t('recordings.totalCount', { count: total }) }}</span>
  </div>
</div>
```

- [ ] **Step 3: Update action button priority**

Replace the actions column template to make play button primary:

```vue
<el-table-column :label="$t('recordings.actions')" width="160" align="center">
  <template #default="{ row }">
    <div class="action-group">
      <!-- Play - Primary action -->
      <el-tooltip
        :content="row.status === 'recording' ? t('recordings.recordingActive') : row.status === 'failed' ? t('recordings.recordingFailed') : t('recordings.play')"
        :show-after="400"
      >
        <el-button
          class="action-btn action-btn--play"
          size="small"
          :icon="VideoPlay"
          :disabled="row.status === 'recording' || row.status === 'failed'"
          :loading="hlsConvertingId === row.id"
          @click="playRecording(row)"
        />
      </el-tooltip>
      
      <!-- Download - Secondary -->
      <el-tooltip :content="$t('recordings.download')" :show-after="400">
        <el-button
          class="action-btn"
          size="small"
          :icon="Download"
          :disabled="row.status === 'recording' || row.status === 'failed'"
          @click="downloadRecording(row)"
        />
      </el-tooltip>
      
      <!-- Delete - Danger -->
      <el-tooltip :content="$t('common.delete')" :show-after="400">
        <el-button
          class="action-btn action-btn--danger"
          size="small"
          :icon="Delete"
          @click="handleDelete(row)"
        />
      </el-tooltip>
    </div>
  </template>
</el-table-column>
```

- [ ] **Step 4: Add CSS for filter section and action priority**

Replace/add styles:

```css
/* Filter section */
.filter-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-bottom: var(--space-6);
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.filter-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.filter-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.summary-count {
  font-size: 13px;
  color: var(--color-text-secondary);
}

/* Action buttons with priority */
.action-group {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
}

.action-btn {
  height: 28px;
  width: 28px;
  padding: 3px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  background: transparent;
  border: 1px solid transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--easing-standard);
}

.action-btn:hover:not(:disabled) {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
}

.action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.action-btn--play {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.action-btn--play:hover:not(:disabled) {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
  color: white;
}

.action-btn--danger:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.1);
  color: var(--color-error);
}
```

Remove old `.filter-bar`, `.action-group`, `.action-btn` styles.

- [ ] **Step 5: Commit**

```bash
git add src/views/RecordingsView.vue
git commit -m "refactor(ui): redesign filter section and action priority in RecordingsView"
```

---

## Phase 4: Global Enhancements

### Task 11: Update MainLayout - Sidebar Grouping & Breadcrumb

**Files:**
- Modify: `src/layout/MainLayout.vue`

- [ ] **Step 1: Read current MainLayout.vue**

Read the existing file.

- [ ] **Step 2: Replace sidebar nav structure with grouped sections**

Replace the nav section:

```vue
<nav class="app-sidebar">
  <div class="nav-section">
    <div class="nav-section-label">{{ $t('layout.overview') }}</div>
    <RouterLink to="/dashboard" class="nav-item" :class="{ active: $route.path === '/dashboard' }">
      <el-icon :size="16"><DataAnalysis /></el-icon>
      <span>{{ $t('layout.dashboard') }}</span>
    </RouterLink>
  </div>
  
  <div class="nav-section">
    <div class="nav-section-label">{{ $t('layout.devices') }}</div>
    <RouterLink to="/devices" class="nav-item" :class="{ active: $route.path === '/devices' }">
      <el-icon :size="16"><Monitor /></el-icon>
      <span>{{ $t('layout.devices') }}</span>
    </RouterLink>
    <RouterLink to="/cameras" class="nav-item" :class="{ active: $route.path === '/cameras' }">
      <el-icon :size="16"><VideoCameraFilled /></el-icon>
      <span>{{ $t('layout.cameras') }}</span>
    </RouterLink>
    <RouterLink to="/topology" class="nav-item" :class="{ active: $route.path === '/topology' }">
      <el-icon :size="16"><Share /></el-icon>
      <span>{{ $t('layout.topology') }}</span>
    </RouterLink>
  </div>
  
  <div class="nav-section">
    <div class="nav-section-label">{{ $t('layout.media') }}</div>
    <RouterLink to="/recordings" class="nav-item" :class="{ active: $route.path === '/recordings' }">
      <el-icon :size="16"><Film /></el-icon>
      <span>{{ $t('layout.recordings') }}</span>
    </RouterLink>
    <RouterLink to="/dlna" class="nav-item" :class="{ active: $route.path === '/dlna' }">
      <el-icon :size="16"><Promotion /></el-icon>
      <span>{{ $t('layout.dlna') }}</span>
    </RouterLink>
  </div>
  
  <div class="nav-section">
    <div class="nav-section-label">{{ $t('layout.system') }}</div>
    <RouterLink to="/members" class="nav-item" :class="{ active: $route.path === '/members' }">
      <el-icon :size="16"><UserFilled /></el-icon>
      <span>{{ $t('layout.members') }}</span>
    </RouterLink>
    <RouterLink to="/schedule" class="nav-item" :class="{ active: $route.path === '/schedule' }">
      <el-icon :size="16"><Clock /></el-icon>
      <span>{{ $t('layout.schedule') }}</span>
    </RouterLink>
    <RouterLink to="/settings" class="nav-item" :class="{ active: $route.path === '/settings' }">
      <el-icon :size="16"><Setting /></el-icon>
      <span>{{ $t('layout.settings') }}</span>
    </RouterLink>
  </div>
</nav>
```

- [ ] **Step 3: Add breadcrumb to content area**

Replace `<main class="app-content">` section:

```vue
<main class="app-content">
  <div class="content-header">
    <el-breadcrumb separator="/">
      <el-breadcrumb-item to="/dashboard">{{ $t('layout.dashboard') }}</el-breadcrumb-item>
      <el-breadcrumb-item v-if="$route.meta.title">{{ $route.meta.title }}</el-breadcrumb-item>
    </el-breadcrumb>
  </div>
  <router-view />
</main>
```

- [ ] **Step 4: Add sidebar and breadcrumb CSS**

Replace the style section:

```css
<style scoped>
/* Sidebar nav sections */
.app-sidebar {
  width: var(--sidebar-width);
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  flex-shrink: 0;
  padding: var(--space-2) 0;
  overflow-y: auto;
}

.nav-section {
  padding: var(--space-1) 0;
}

.nav-section + .nav-section {
  border-top: 1px solid var(--color-border-subtle);
  margin-top: var(--space-2);
  padding-top: var(--space-4);
}

.nav-section:first-child {
  border-top: none;
}

.nav-section-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-muted);
  padding: var(--space-2) var(--space-4);
  margin-bottom: var(--space-1);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 36px;
  padding: 0 var(--space-4);
  font-size: 13px;
  color: var(--color-text-secondary);
  text-decoration: none;
  position: relative;
  transition: background var(--duration-fast) var(--easing-standard),
              color var(--duration-fast) var(--easing-standard);
}

.nav-item:hover {
  background: var(--color-surface-raised);
  color: var(--color-text-primary);
}

.nav-item.active {
  background: var(--color-primary-subtle);
  color: var(--color-primary);
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  background: var(--color-primary);
  border-radius: 0 var(--radius-xs) var(--radius-xs) 0;
}

.nav-item .el-icon {
  flex-shrink: 0;
  font-size: 16px;
}

/* Content area with breadcrumb */
.app-content {
  flex: 1;
  overflow-y: auto;
  background: var(--color-bg);
  padding: var(--space-6);
}

.content-header {
  margin-bottom: var(--space-6);
}

:deep(.el-breadcrumb) {
  font-size: 13px;
}

:deep(.el-breadcrumb__item) {
  color: var(--color-text-muted);
}

:deep(.el-breadcrumb__inner) {
  color: var(--color-text-secondary);
}

:deep(.el-breadcrumb__inner.is-link:hover) {
  color: var(--color-primary);
}

:deep(.el-breadcrumb__separator) {
  color: var(--color-text-muted);
}

/* Keep existing header and other styles */
</style>
```

- [ ] **Step 5: Commit**

```bash
git add src/layout/MainLayout.vue
git commit -m "feat(ui): add sidebar grouping and breadcrumb navigation"
```

---

### Task 12: Final Review and Verification

**Files:**
- All modified files

- [ ] **Step 1: Run dev server to verify**

```bash
npm run dev
# or
pnpm dev
```

Open browser and verify:
- Dashboard shows new StatCard grid with glass effect
- Activity feed has scroll fade
- Devices page shows card grid layout
- Camera page has grouped action dropdown
- Recordings page has redesigned filter bar
- Sidebar has grouped navigation with breadcrumb

- [ ] **Step 2: Check for console errors**

Open browser DevTools, check Console tab for any errors.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat(ui): complete UI redesign - refined tech aesthetic with glass effects

- Design system: updated colors, spacing, animations
- Components: StatCard, ActivityFeed, FilterChip, EmptyState
- Views: Dashboard, Devices, Camera, Recordings redesigned
- Global: sidebar grouping, breadcrumb navigation
"
```

---

## Implementation Summary

| Phase | Task | Description |
|-------|------|-------------|
| 1 | 1 | Design system foundation in style.css |
| 2 | 2 | StatCard component |
| 2 | 3 | ActivityFeed component |
| 2 | 4 | FilterChip component |
| 2 | 5 | EmptyState component |
| 2 | 6 | DeviceCard redesign |
| 3 | 7 | DashboardView update |
| 3 | 8 | DevicesView update |
| 3 | 9 | CameraView update |
| 3 | 10 | RecordingsView update |
| 4 | 11 | MainLayout sidebar & breadcrumb |
| 4 | 12 | Final review & verification |

---

## Self-Review Checklist

- [ ] All CSS variables use `--` prefix and match spec
- [ ] All animation names use kebab-case
- [ ] All components have scoped styles
- [ ] No hardcoded colors - use CSS variables
- [ ] Consistent spacing using `--space-*` scale
- [ ] All interactive elements have hover/focus states
- [ ] Icons use consistent 16px size
- [ ] No placeholder text or TODO comments
