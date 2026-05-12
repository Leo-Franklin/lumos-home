# Smart Home Frontend UI Redesign Spec

**Date:** 2026-05-12
**Status:** Approved
**Version:** 1.0

---

## 1. Concept & Vision

全面重构智能家居前端界面，采用 **精致科技感** 风格。参考 Linear/Vercel Dashboard 的设计语言：深色主题、玻璃拟态、微妙光晕、流畅动效。目标是打造一个专业、精致、信息密度适中的智能家居控制台。

---

## 2. Design System

### 2.1 Color Palette

```css
/* Primary - 精致紫色 */
--color-primary:        #6366F1;
--color-primary-hover:  #4F46E5;
--color-primary-subtle: rgba(99, 102, 241, 0.12);
--color-primary-border: rgba(99, 102, 241, 0.30);

/* Dark Canvas - 增加层次 */
--color-bg:              #0F0F12;
--color-surface:         #18181C;
--color-surface-raised:  #222228;
--color-surface-overlay: #2A2A32;
--color-border:          #32323C;
--color-border-subtle:   #28282E;

/* Text - 提升对比度 */
--color-text-primary:   #F4F4F6;
--color-text-secondary: #A0A0AB;
--color-text-muted:     #6B6B76;

/* Semantic Colors */
--color-online:   #10B981;
--color-offline:  #6B7280;
--color-error:    #EF4444;
--color-warning:  #F59E0B;
--color-success:  #10B981;
```

### 2.2 Typography

```css
--font-display: "Outfit", sans-serif;
--font-sans: "Noto Sans SC", "PingFang SC", "Hiragino Sans GB", sans-serif;
--font-mono: "JetBrains Mono", "Fira Code", monospace;
```

### 2.3 Spacing (4px base)

```css
--space-1: 4px;  --space-2: 8px;  --space-3: 12px;
--space-4: 16px; --space-5: 20px; --space-6: 24px;
--space-8: 32px; --space-10: 40px;
```

### 2.4 Motion

```css
--easing-standard: cubic-bezier(0.4, 0, 0.2, 1);
--easing-decelerate: cubic-bezier(0, 0, 0.2, 1);
--easing-spring: cubic-bezier(0.34, 1.56, 0.64, 1);

--duration-fast: 100ms;  --duration-base: 200ms;
--duration-slow: 300ms;  --duration-slower: 400ms;

@keyframes fade-up { from { opacity: 0; transform: translateY(8px); } }
@keyframes fade-in { from { opacity: 0; } }
@keyframes pulse-glow { 0%,100% { box-shadow: 0 0 0 0 rgba(16,185,129,0.5); } 50% { box-shadow: 0 0 0 6px rgba(16,185,129,0); } }
```

### 2.5 Glass Effect

```css
.glass-card {
  background: rgba(24, 24, 28, 0.8);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
}
```

---

## 3. Components

### 3.1 StatCard

- `glass-card` 背景 + 内边距 20px
- 图标区 44px，带内阴影
- 数值 32px/700 Outfit
- 趋势指示器（可选）：如 "+2 vs last week"
- 关键状态使用 `glow-border` 强调

### 3.2 ActivityFeed

- 最大高度 420px，超出部分滚动
- 底部渐变遮罩 `.activity-fade` 提示可滚动
- 每条项目包含：彩色圆点 + 标签 + 时间
- 交错入场动画 `fade-up`

### 3.3 FilterChip

- Pill shape: `border-radius: 9999px`
- 选中时填充对应设备颜色（10% opacity 背景 + 文字色）
- 左侧 6px 彩色圆点

### 3.4 EmptyState

- 居中布局
- 简洁 SVG 插图（设备+云+问号）
- 标题 + 描述 + 操作按钮

### 3.5 ActionDropdown

- 主操作按钮（填充样式）
- 次要操作收起在 dropdown

---

## 4. Views

### 4.1 DashboardView

**布局:**
```
PageHeader: 标题 + 刷新按钮
StatsGrid:  5个 StatCard (auto-fit, minmax 180px)
ActivityPanel: ActivityFeed
```

**StatCard 动画:** 交错 `fade-up`，delay 0/40/80/120/160ms

**ActivityFeed:** 底部渐变遮罩，右上角「查看全部」按钮

### 4.2 DevicesView

**设备卡片化:**
- `glass-card` 容器
- 左上角：状态点 + 类型图标
- 内容：设备名、IP、厂商、在线时长
- 操作按钮始终可见（去掉 hover 依赖）
- 支持缩略图区域

**筛选栏:**
- el-input 带 search 图标
- FilterChip 替代全大写按钮
- 去掉 All 按钮，改用「全部」chip

### 4.3 CameraView

**操作按钮重组:**
```
[探测] [预览 ▼] ──────── [编辑] [录制] [删除]
```
- 预览改为 dropdown，包含：实时预览、截图、HLS直播
- 录制状态使用脉冲动画

**表格优化:**
- MAC 列：显示设备名，hover tooltip 显示完整 MAC
- RTSP URL：truncated + tooltip

### 4.4 RecordingsView

**Filter Bar:**
```vue
<div class="filter-section">
  <div class="filter-row">
    <el-select> <el-date-picker> <el-button type="primary">
  </div>
  <div class="filter-summary">共 {{ total }} 条</div>
</div>
```

**操作按钮优先级:**
- 播放：填充主按钮
- 下载/删除：ghost 按钮

---

## 5. Global Improvements

### 5.1 Sidebar Navigation

分组结构：
- Overview: Dashboard
- Devices: Devices, Cameras, Topology
- Media: Recordings, DLNA
- System: Members, Schedule, Settings

分组之间 8px 间距，选中项左侧 3px 主色竖条。

### 5.2 Breadcrumb

在 `.app-content` 顶部添加面包屑导航。

### 5.3 Accessibility

- 所有文字对比度 ≥ 4.5:1
- 键盘可导航（focus 状态）
- ARIA 标签

---

## 6. Implementation Phases

**Phase 1: Design System Foundation**
- style.css 全局变量更新
- 动效系统完善

**Phase 2: Core Components**
- StatCard / ActivityFeed / EmptyState
- FilterChip / ActionDropdown

**Phase 3: View Redesigns**
- DashboardView
- DevicesView
- CameraView
- RecordingsView

**Phase 4: Global Enhancements**
- Sidebar 分组
- Breadcrumb
- Font/Contrast fixes

---

## 7. Files to Modify

| File | Changes |
|------|---------|
| `src/style.css` | 全局变量、动效、组件样式 |
| `src/views/DashboardView.vue` | StatCard 网格、ActivityFeed |
| `src/views/DevicesView.vue` | 卡片化、FilterChip |
| `src/views/CameraView.vue` | 操作按钮分组、表格优化 |
| `src/views/RecordingsView.vue` | Filter bar 重构、操作按钮优先级 |
| `src/layout/MainLayout.vue` | Sidebar 分组、面包屑 |
| `src/components/StatCard.vue` | 新组件 |
| `src/components/ActivityFeed.vue` | 新组件 |
| `src/components/FilterChip.vue` | 新组件 |
| `src/components/EmptyState.vue` | 新组件 |
| `src/components/DeviceCard.vue` | 重构 |
