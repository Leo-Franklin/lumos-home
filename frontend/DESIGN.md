# Smart Home Frontend — Design System

**Source of truth:** `src/style.css` (`:root` token table). This document is the human-readable mirror of those tokens.
**Archetype:** 技术仪表盘 · 深色 · 信息密集
**Atmosphere:** 精准、高效、实时。每个像素都服务于状态感知与设备控制。专业用户导向，强调信息密度与操作效率。

> **历史背景：** 早期版本基于 Linear 设计系统（`#5E5CE6` / `#26C281` / `#1E1E20`），与 `MainLayout` 浅色版本并存导致风格断层。
> 当前 `src/style.css` 已迁移到 Indigo 体系（`#6366F1` / `#10B981` / `#0F0F12`），全局统一深色主题。
> 本文件与 `src/style.css` 严格同步；如调整颜色，先改 `style.css`，再回填本文件。

---

## 1. 视觉主题与氛围

**整体基调：** 深色技术仪表盘，冷感蓝紫主色（Indigo），高对比度状态色。
**核心关键词：** 精准 · 实时 · 可控 · 专业 · 信息密集

- 全局深色主题（无浅色页面）
- 状态色作为语言系统（在线=绿、离线=灰、告警=橙/红、扫描=琥珀）
- 排版偏小（14px base），服务信息密度
- 动画极简，仅用于状态变化，不做装饰

---

## 2. 色彩系统

> 以下值直接来自 `src/style.css` 的 `:root` 块。所有组件必须通过 `var(--color-*)` 引用，
> 禁止硬编码 hex / rgba（`src/components/charts/chartColors.js` 例外，作为图表 JS 端颜色源）。

### 主色（Indigo）
| Token | Hex / RGBA | 用途 |
|-------|-----------|------|
| `--color-primary` | `#6366F1` | CTA 按钮、激活状态、链接、强调色 |
| `--color-primary-hover` | `#4F46E5` | 悬停态 |
| `--color-primary-subtle` | `rgba(99, 102, 241, 0.12)` | 轻量高亮、选中行背景、tag 背景 |
| `--color-primary-border` | `rgba(99, 102, 241, 0.30)` | 激活边框、轮廓 |

### 深色画布
| Token | Hex | 用途 |
|-------|-----|------|
| `--color-bg` | `#0F0F12` | 页面底色（最深） |
| `--color-surface` | `#18181C` | 卡片、侧边栏、列表行背景（首层） |
| `--color-surface-raised` | `#222228` | 悬停行、次级面板（次层） |
| `--color-surface-overlay` | `#2A2A32` | 下拉菜单、模态框（最高层） |
| `--color-border` | `#32323C` | 分割线、卡片边框 |
| `--color-border-subtle` | `#28282E` | 极细分割、嵌套边框 |

### 文字
| Token | Hex | 用途 |
|-------|-----|------|
| `--color-text-primary` | `#F4F4F6` | 主文字、设备名称、标题 |
| `--color-text-secondary` | `#A0A0AB` | 辅助信息、IP 地址、描述 |
| `--color-text-muted` | `#6B6B76` | 时间戳、元数据、禁用状态 |
| `--color-text-inverse` | `#FFFFFF` | 按钮上的白色文字 |

### 语义色
| 状态 | Token | Hex | 用途 |
|------|-------|-----|------|
| 在线 | `--color-online` | `#10B981` | 在线指示点、徽章、录制状态 |
| 离线 | `--color-offline` | `#6B7280` | 离线指示点、灰色徽章 |
| 成功 | `--color-success` | `#10B981` | 成功提示、确认 |
| 错误 | `--color-error` | `#EF4444` | 删除按钮 hover、连接失败、错误 |
| 警告 | `--color-warning` | `#F59E0B` | 警告状态、IO 设备色 |
| 扫描中 | `--color-scanning` | `#F59E0B` | 扫描进度条、活跃任务 |

### 设备类型色
| 设备类型 | Token | Hex |
|---------|-------|-----|
| 摄像头 | `--color-type-camera` | `#6366F1` |
| 电脑 | `--color-type-computer` | `#10B981` |
| 手机 | `--color-type-phone` | `#F59E0B` |
| IoT | `--color-type-iot` | `#F97316` |
| 未知 | `--color-type-unknown` | `#6B7280` |
| 路由器 | `--color-type-router` | `#06B6D4` |
| 平板 | `--color-type-tablet` | `#D946EF` |
| 电视 | `--color-type-tv` | `#8B5CF6` |
| 打印机 | `--color-type-printer` | `#14B8A6` |
| 智能音箱 | `--color-type-smart-speaker` | `#84CC16` |
| 游戏机 | `--color-type-game-console` | `#EF4444` |
| NAS | `--color-type-nas` | `#3B82F6` |
| 可穿戴 | `--color-type-wearable` | `#EC4899` |

### 活动流分类色（Activity Feed）
| 分类 | Token | Hex |
|------|-------|-----|
| 设备事件 | `--color-cat-device` | `#3B82F6` |
| 摄像头事件 | `--color-cat-camera` | `#10B981` |
| 成员事件 | `--color-cat-member` | `#6366F1` |
| 系统事件 | `--color-cat-system` | `#6B7280` |

### Stat Card 图标强调色
| 卡片 | Token | Hex |
|------|-------|-----|
| 成员 | `--color-accent-members` | `#6366F1` |
| 摄像头 | `--color-accent-cameras` | `#10B981` |
| 网络设备 | `--color-accent-devices` | `#3B82F6` |
| 录像 | `--color-accent-recordings` | `#F59E0B` |
| 未知设备 | `--color-accent-unknown` | `#6B7280` |
| 未知设备（警告） | `--color-accent-unknown-warn` | `#F59E0B` |

> **设计原则：** 紫=主色/摄像头/成员，绿=成功/在线/电脑/摄像头事件，黄=进行中/手机/警告，橙=警告/IoT。
> 状态色与类型色刻意复用，减少颜色总量，降低认知负担。

---

## 3. 字体排版

字体来源：Google Fonts，CSS 顶部 `@import` 加载。

```css
--font-display: "Outfit", -apple-system, BlinkMacSystemFont, sans-serif;     /* 数字、显示 */
--font-sans:    "Noto Sans SC", "PingFang SC", "Hiragino Sans GB",
                "Microsoft YaHei", sans-serif;                               /* 正文（中文优先） */
--font-mono:    "JetBrains Mono", "Fira Code", Consolas, monospace;          /* MAC/IP */
--font-tabular: "Outfit", monospace;                                         /* 等宽数字 */
```

> **字体选择理由：** `Outfit` 几何感强、可读性高，用于数字展示；`Noto Sans SC` 完整覆盖简中/繁中/日韩字形，
> 比系统回退更稳定；`JetBrains Mono` 提供等宽标识符的清晰识别。

| Token | 大小 | 字重 | 行高 | 字距 | 用途 |
|-------|------|------|------|------|------|
| `--text-xs` | 11px | 400 | 1.4 | +0.01em | 标签、徽章 |
| `--text-sm` | 12px | 400 | 1.5 | 0 | IP 地址、时间戳、元数据 |
| `--text-base` | 14px | 400 | 1.5 | 0 | 正文、列表项主文字 |
| `--text-lg` | 15px | 500 | 1.5 | -0.01em | 设备名称（强调）|
| `--text-xl` | 18px | 600 | 1.4 | -0.02em | 页面副标题 |
| `--text-2xl` | 22px | 700 | 1.3 | -0.02em | 页面主标题 |
| `--text-3xl` | 28px | 700 | 1.2 | -0.03em | 大数字、统计数据 |

**数字显示：** 统计数据使用 `font-variant-numeric: tabular-nums` + `letter-spacing: -0.03em`，确保数字等宽对齐，视觉更紧凑。

**Mono 字体用途：** MAC 地址、IP 地址、录像文件名、设备 ID — 凡是机器生成的标识符均用 mono。

---

## 4. 间距与布局

**基础单位：** 4px  
**间距序列：** `4, 8, 12, 16, 20, 24, 32, 40`

| Token | 值 | 用途 |
|-------|---|------|
| `--space-1` | 4px | 图标与文字间距 |
| `--space-2` | 8px | 组件内部间距 |
| `--space-3` | 12px | 列表项内边距（紧凑） |
| `--space-4` | 16px | 标准间距、按钮内边距 |
| `--space-5` | 20px | 卡片内边距 |
| `--space-6` | 24px | 内容区内边距 |
| `--space-8` | 32px | 区块间距 |
| `--space-10` | 40px | 页面级间距 |

**页面布局：**
```
┌─────────────────────────────────────────────┐
│  Header  56px  bg: --color-surface          │
├──────────┬──────────────────────────────────┤
│          │                                  │
│ Sidebar  │  Content Area                    │
│  220px   │  bg: --color-bg                  │
│  bg:     │  padding: 24px                   │
│  surface │  max-width: 1400px               │
│          │                                  │
└──────────┴──────────────────────────────────┘
```

- **Header 高度：** 56px
- **Sidebar 宽度：** 220px（展开），48px（收起）
- **内容最大宽度：** 1400px
- **内容内边距：** 24px

---

## 5. 圆角

| Token | 值 | 用途 |
|-------|---|------|
| `--radius-xs` | 3px | 标签、键盘快捷键 chip |
| `--radius-sm` | 4px | 按钮、输入框、徽章 |
| `--radius-md` | 6px | 卡片、设备行、下拉菜单 |
| `--radius-lg` | 8px | 模态框、面板、对话框 |
| `--radius-xl` | 12px | glass-card |
| `--radius-full` | 9999px | 状态指示点、在线/离线 pill |

---

## 6. 阴影与层级

深色模式下通过**背景色深浅**传达层级，不依赖阴影。

```css
/* 深色模式：背景色即层级 */
--color-bg              /* 最底层：页面 */
--color-surface         /* 第一层：卡片、侧边栏 */
--color-surface-raised  /* 第二层：悬停、激活 */
--color-surface-overlay /* 最高层：下拉、模态 */

/* 仅在浮层上使用轻微阴影 */
--shadow-sm:    0 1px 4px rgba(0, 0, 0, 0.5);
--shadow-md:    0 4px 12px rgba(0, 0, 0, 0.6);
--shadow-lg:    0 8px 24px rgba(0, 0, 0, 0.7);
--shadow-focus: 0 0 0 2px rgba(99, 102, 241, 0.4);
```

---

## 7. 组件模式

### Header（顶部导航栏）
```
高度: 56px
背景: --color-surface
下边框: 1px solid --color-border
内容: Logo（左）| WebSocket 连接状态（中右）| 用户头像+下拉（右）

WebSocket 状态指示:
  已连接: 绿点 (--color-online) + text-muted
  断开:   灰点 (--color-offline) + text-muted
  重连中: 黄点闪烁 (--color-scanning)
```

### Sidebar（侧边栏）
```
宽度: 220px
背景: --color-surface
右边框: 1px solid --color-border

导航项:
  高度: 36px
  内边距: 0 16px
  图标: 16px, --color-text-muted
  文字: text-sm --color-text-secondary

  hover:  bg --color-surface-raised, text-primary
  active: bg --color-primary-subtle, text-primary,
          左侧 3px accent 条 --color-primary
```

### 设备列表行（DeviceCard）
```
状态指示点:
  在线: 10px 圆点, background: --color-online,
         box-shadow: 0 0 8px rgba(16, 185, 129, 0.5), pulse-glow 2s
  离线: 10px 圆点, background: --color-offline

类型图标区 (32x32):
  背景: color-mix(in srgb, [type-color] 10%, transparent)
  图标色: [type-color]

类型徽章 (Type Badge Pill):
  背景: color-mix(in srgb, [type-color] 10%, transparent)
  文字: [type-color], text-xs, weight: 500
  radius: --radius-full, padding: 2px 10px
```

### 按钮
```
Primary:   bg var(--color-primary), text --color-text-inverse,
           radius --radius-sm, height 32px, px 12px, text-sm
           hover: bg var(--color-primary-hover), 150ms

Secondary: bg --color-surface-raised, border 1px --color-border,
           text --color-text-secondary, radius --radius-sm, height 32px

Ghost:     transparent, text --color-text-secondary
           hover: bg --color-surface-raised, text-primary

Danger:    默认同 Ghost, hover: bg rgba(239, 68, 68, 0.1), text --color-error
```

### 输入框 / 搜索框
```
高度: 32px
背景: --color-surface-raised
边框: 1px solid --color-border (wrapper inset)
圆角: --radius-sm
内边距: 0 12px
文字: text-sm --color-text-primary
占位符: --color-text-muted

focus: border-color --color-primary, box-shadow: --shadow-focus
```

### 模态框 / 对话框
```
蒙层: rgba(0, 0, 0, 0.6) backdrop
面板背景: --color-surface-overlay
边框: 1px solid --color-border
圆角: --radius-lg
阴影: --shadow-lg
内边距: 24px
```

### 状态徽章（在线/离线 Pill）
```
在线: bg rgba(16, 185, 129, 0.15), text --color-online,
      radius full, px: 8 py: 2, text-xs weight: 500
离线: bg rgba(107, 114, 128, 0.2), text --color-offline,
      radius full, px: 8 py: 2, text-xs weight: 500
```

### 摄像头播放器
```
容器: bg #000000, radius --radius-md
最大高度: 480px
无信号状态: 图标 #f56c6c, padding 20px
```

### 通知 / Toast
```
容器: bg --color-surface-overlay, border 1px --color-border,
      radius --radius-md, shadow --shadow-lg
最大宽度: 360px

类型:
  成功: 左边 3px 实线 --color-online
  错误: 左边 3px 实线 --color-error
  警告: 左边 3px 实线 --color-warning
  信息: 左边 3px 实线 --color-primary
```

### 表单（设置页 / 编辑对话框）
```
标签: text-sm --color-text-secondary, margin-bottom: 4px
输入框: 同"输入框"规格
错误提示: text-xs --color-error, margin-top: 4px
表单组间距: 16px
```

---

## 8. 动效与过渡

```css
--duration-fast:   100ms;
--duration-base:   200ms;
--duration-slow:   300ms;
--duration-slower: 400ms;
--easing-standard: cubic-bezier(0.4, 0, 0.2, 1);
--easing-snap:     cubic-bezier(0.16, 1, 0.3, 1);
--easing-spring:   cubic-bezier(0.34, 1.56, 0.64, 1);
```

**动效规则：**
- 列表行进入：`opacity 0→1 + translateY(8px→0)`，200ms
- Stat Card 入场：stagger 0–160ms
- 状态指示点（在线）：`pulse-glow` 2s infinite
- 扫描进度：`width` 过渡 300ms
- 模态框：`opacity + scale` 300ms
- WebSocket 重连点：闪烁 `opacity 1→0.5` 1s infinite（仅重连时）

---

## 9. 设计护栏

**必须遵守：**
- 全局使用深色主题，不引入浅色背景页面
- 所有颜色使用 CSS 变量，禁止在组件内硬编码 hex 值（`src/components/charts/chartColors.js` 作为图表 JS 端颜色源除外）
- IP 地址、MAC 地址、文件名等机器标识符一律使用 mono 字体
- 状态色用于传达含义，不用于美化（绿色=在线，不是"好看"）
- Element Plus 组件通过 CSS 变量覆盖（不修改 element-plus 源码）
- 修改任何 token，先改 `src/style.css`，再回填本文件

**禁止：**
- 不在深色页面上放置纯白（`#FFF`）大块背景
- 不使用大圆角（>8px）在列表项或表格行上
- 不用卡片网格布局展示设备列表主内容（用行列表，信息密度更高）
- 不添加纯装饰性动画（旋转、弹跳等）
- 不在没有操作意图的情况下堆叠多个模态框
- 不用颜色深浅表达层级（要用背景色 token 系统，不用 opacity 叠加）

---

## 附录：CSS 变量声明（根文件）

> 与 `src/style.css` `:root` 块保持一致。完整变量（含 Element Plus 覆盖）请直接阅读 `src/style.css`。

```css
:root {
  /* 主色 */
  --color-primary:        #6366F1;
  --color-primary-hover:  #4F46E5;
  --color-primary-subtle: rgba(99, 102, 241, 0.12);
  --color-primary-border: rgba(99, 102, 241, 0.30);

  /* 深色画布 */
  --color-bg:              #0F0F12;
  --color-surface:         #18181C;
  --color-surface-raised:  #222228;
  --color-surface-overlay: #2A2A32;
  --color-border:          #32323C;
  --color-border-subtle:   #28282E;

  /* 文字 */
  --color-text-primary:   #F4F4F6;
  --color-text-secondary: #A0A0AB;
  --color-text-muted:     #6B6B76;
  --color-text-inverse:   #FFFFFF;

  /* 语义色 */
  --color-online:   #10B981;
  --color-offline:  #6B7280;
  --color-error:    #EF4444;
  --color-warning:  #F59E0B;
  --color-success:  #10B981;
  --color-scanning: #F59E0B;

  /* 设备类型色 */
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

  /* 圆角 */
  --radius-xs:   3px;
  --radius-sm:   4px;
  --radius-md:   6px;
  --radius-lg:   8px;
  --radius-xl:   12px;
  --radius-full: 9999px;

  /* 阴影 */
  --shadow-sm:    0 1px 4px rgba(0, 0, 0, 0.5);
  --shadow-md:    0 4px 12px rgba(0, 0, 0, 0.6);
  --shadow-lg:    0 8px 24px rgba(0, 0, 0, 0.7);
  --shadow-focus: 0 0 0 2px rgba(99, 102, 241, 0.4);

  /* 动效 */
  --duration-fast:   100ms;
  --duration-base:   200ms;
  --duration-slow:   300ms;
  --duration-slower: 400ms;

  /* 布局 */
  --sidebar-width:           220px;
  --sidebar-width-collapsed: 48px;
  --header-height:           56px;
  --content-max-width:       1400px;

  /* 字体 */
  --font-display: "Outfit", -apple-system, BlinkMacSystemFont, sans-serif;
  --font-sans:    "Noto Sans SC", "PingFang SC", "Hiragino Sans GB",
                  "Microsoft YaHei", sans-serif;
  --font-mono:    "JetBrains Mono", "Fira Code", Consolas, monospace;
  --font-tabular: "Outfit", monospace;
}
```
