# Smart Home Frontend — Design System

**Base:** Linear (Dark Mode)
**Archetype:** 技术仪表盘 · 深色 · 信息密集
**Atmosphere:** 精准、高效、实时。每个像素都服务于状态感知与设备控制。专业用户导向，强调信息密度与操作效率。

> **选型依据：** 现有代码（DeviceCard.vue、DevicesView.vue）已自发采用 Linear 的完整色彩系统，
> 从 `#5E5CE6`（主色）到 `#26C281`（在线/成功）再到 `#1E1E20`（卡片背景）均精确吻合。
> 本文件将这一隐式选择正式化，并将其扩展为完整的设计语言，消除当前 MainLayout（浅色）
> 与 DeviceCard（深色）之间的风格断层。

---

## 1. 视觉主题与氛围

**整体基调：** 深色技术仪表盘，冷感紫蓝主色，高对比度状态色。  
**核心关键词：** 精准 · 实时 · 可控 · 专业 · 信息密集

- 全局深色主题，消除浅色/深色混搭
- 状态色作为语言系统（在线=绿、离线=灰、告警=橙/红）
- 排版偏小（14px base），服务信息密度
- 动画极简，仅用于状态变化，不做装饰

---

## 2. 色彩系统

### 主色（Linear Purple）
| Token | Hex | 用途 |
|-------|-----|------|
| `--color-primary` | `#5E5CE6` | CTA 按钮、激活状态、链接、摄像头类型标签 |
| `--color-primary-hover` | `#4E4CCF` | 悬停态 |
| `--color-primary-subtle` | `rgba(94,92,230,0.15)` | 轻量高亮、选中行背景 |
| `--color-primary-border` | `rgba(94,92,230,0.35)` | 激活边框 |

### 深色画布
| Token | Hex | 用途 |
|-------|-----|------|
| `--color-bg` | `#161618` | 页面底色 |
| `--color-surface` | `#1E1E20` | 卡片、侧边栏、列表行背景 |
| `--color-surface-raised` | `#252528` | 悬停行、次级面板 |
| `--color-surface-overlay` | `#2C2C2F` | 下拉菜单、模态框背景 |
| `--color-border` | `#2F2F33` | 分割线、卡片边框 |
| `--color-border-subtle` | `#28282B` | 极细分割、嵌套边框 |

### 文字
| Token | Hex | 用途 |
|-------|-----|------|
| `--color-text-primary` | `#E8E8EC` | 主文字、设备名称、标题 |
| `--color-text-secondary` | `#8B8B96` | 辅助信息、IP 地址、描述 |
| `--color-text-muted` | `#56565E` | 时间戳、元数据、禁用状态 |
| `--color-text-inverse` | `#FFFFFF` | 按钮上的白色文字 |

### 设备状态色（语义系统）
| 状态 | Token | Hex | 用途 |
|------|-------|-----|------|
| 在线 | `--color-online` | `#26C281` | 在线指示点、在线徽章背景（透明度 15%）|
| 离线 | `--color-offline` | `#56565E` | 离线指示点、灰色徽章 |
| 告警/错误 | `--color-error` | `#F05252` | 删除按钮 hover、连接失败 |
| 扫描中 | `--color-scanning` | `#F2C94C` | 扫描进度条、活跃任务 |
| 高优先级 | `--color-warning` | `#F07D38` | 警告状态、重要通知 |
| 信息 | `--color-info` | `#5E5CE6` | 提示信息（与主色复用）|

### 设备类型色（Type Badge System）
| 设备类型 | Token | Hex | 说明 |
|---------|-------|-----|------|
| 摄像头 | `--color-type-camera` | `#5E5CE6` | 紫色 = 主色复用 |
| 电脑 | `--color-type-computer` | `#26C281` | 绿色 = 在线色复用 |
| 手机 | `--color-type-phone` | `#F2C94C` | 黄色 |
| IoT | `--color-type-iot` | `#F07D38` | 橙色 |
| 未知 | `--color-type-unknown` | `#8B8B96` | 灰色 = 次文字色复用 |

> **设计原则：** 类型色与语义状态色刻意复用，减少颜色总量，降低认知负担。
> 紫=主色/摄像头，绿=成功/在线/电脑，黄=进行中/手机，橙=警告/IoT。

---

## 3. 字体排版

```css
--font-sans: "Inter", -apple-system, BlinkMacSystemFont, "PingFang SC",
             "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
--font-mono: "JetBrains Mono", "Fira Code", Consolas, monospace;
```

> **中文支持：** Inter 不含中文字形，系统回退顺序为 PingFang SC（macOS）→ Hiragino Sans GB → 
> Microsoft YaHei（Windows），确保中文排版与英文字重视觉统一。

| Token | 大小 | 字重 | 行高 | 字距 | 用途 |
|-------|------|------|------|------|------|
| `--text-xs` | 11px | 400 | 1.4 | +0.01em | 标签、徽章 |
| `--text-sm` | 12px | 400 | 1.5 | 0 | IP 地址、时间戳、元数据 |
| `--text-base` | 14px | 400 | 1.5 | 0 | 正文、列表项主文字 |
| `--text-lg` | 15px | 500 | 1.5 | -0.01em | 设备名称（强调）|
| `--text-xl` | 18px | 600 | 1.4 | -0.02em | 页面副标题 |
| `--text-2xl` | 22px | 700 | 1.3 | -0.02em | 页面主标题 |
| `--text-3xl` | 28px | 700 | 1.2 | -0.03em | 大数字、统计数据 |

**Mono 字体用途：** MAC 地址、IP 地址、录像文件名、设备 ID — 凡是机器生成的标识符均用 mono。

---

## 4. 间距与布局

**基础单位：** 4px  
**间距序列：** `2, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64`

| Token | 值 | 用途 |
|-------|---|------|
| `--space-1` | 4px | 图标与文字间距 |
| `--space-2` | 8px | 组件内部间距 |
| `--space-3` | 12px | 列表项内边距（紧凑） |
| `--space-4` | 16px | 标准间距、按钮内边距 |
| `--space-6` | 24px | 卡片内边距、分组间距 |
| `--space-8` | 32px | 区块间距 |
| `--space-12` | 48px | 页面级间距 |

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

- **Header 高度：** 56px（统一，替换当前混用值）
- **Sidebar 宽度：** 220px（展开），48px（收起）
- **内容最大宽度：** 1400px
- **内容内边距：** 24px

---

## 5. 圆角

| Token | 值 | 用途 |
|-------|---|------|
| `--radius-xs` | 3px | 标签（tag）、键盘快捷键 chip |
| `--radius-sm` | 4px | 按钮、输入框、徽章 |
| `--radius-md` | 6px | 卡片、设备行、下拉菜单 |
| `--radius-lg` | 8px | 模态框、面板、对话框 |
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
--shadow-sm:    0 1px 4px rgba(0,0,0,0.5);
--shadow-md:    0 4px 12px rgba(0,0,0,0.6);
--shadow-lg:    0 8px 24px rgba(0,0,0,0.7);
--shadow-focus: 0 0 0 2px rgba(94,92,230,0.4);
```

---

## 7. 组件模式

### Header（顶部导航栏）
```
高度: 56px
背景: --color-surface
下边框: 1px solid --color-border
内容: Logo（左）| WebSocket 连接状态（中右）| 用户头像+下拉（右）

WebSocket 状态指示：
  已连接: 绿点 (#26C281) + "已连接" text-muted
  断开:   灰点 (#56565E) + "未连接" text-muted  
  重连中: 黄点闪烁 (#F2C94C)
```

### Sidebar（侧边栏）
```
宽度: 220px
背景: --color-surface（与内容区颜色一致，通过右边框区分）
右边框: 1px solid --color-border

导航项:
  高度: 32px
  内边距: 0 12px
  图标: 16px, --color-text-muted
  文字: text-sm --color-text-secondary
  
  hover:  bg --color-surface-raised, text-primary
  active: bg --color-primary-subtle, text-primary,
          左侧 2px accent 条 --color-primary

分组标题: text-xs uppercase letter-spacing:0.06em --color-text-muted, padding: 16px 12px 4px
```

### 设备列表行（DeviceCard）
```
高度: 52px（舒适模式）或 44px（紧凑模式）
背景: transparent（在 --color-bg 上）或 --color-surface（在卡片中）
下边框: 1px solid --color-border-subtle
内边距: 0 16px
hover: bg --color-surface-raised

布局（从左到右）:
  [状态指示点 8px] [类型图标 32x32 rounded-md] [设备名称+IP] [... 弹性占位] [MAC 地址] [类型徽章] [操作按钮]

状态指示点:
  在线: 8px 圆点, background: #26C281, box-shadow: 0 0 6px rgba(38,194,129,0.5)
  离线: 8px 圆点, background: #56565E

类型图标区:
  32x32px, radius: --radius-md
  背景: rgba([type-color], 0.15)
  图标色: [type-color]

设备名称: text-base --color-text-primary font-weight:500
IP 地址:  text-sm --color-text-muted font-mono（mono 字体）
MAC 地址: text-xs --color-text-muted font-mono，仅 hover 时完整显示

类型徽章 (Type Badge):
  背景: rgba([type-color], 0.15)
  文字: [type-color], text-xs, weight:500
  radius: --radius-full, padding: 2px 8px

操作按钮（hover 时出现）:
  编辑: Ghost 按钮, icon-only, hover text-primary
  删除: Ghost 按钮, icon-only, hover text-error
```

### 按钮
```
Primary:   bg #5E5CE6, text white, radius 4px, height 32px, px 12px, text-sm
           hover: bg #4E4CCF, transition 150ms

Secondary: bg --color-surface-raised, border 1px --color-border,
           text --color-text-secondary, radius 4px, height 32px

Ghost:     transparent, text --color-text-secondary
           hover: bg --color-surface-raised, text-primary

Danger:    默认同 Ghost, hover: bg rgba(240,82,82,0.1), text #F05252

Icon-only: 28x28px, radius --radius-sm
           hover: bg --color-surface-raised

Disabled:  opacity: 0.4, cursor: not-allowed
```

### 输入框 / 搜索框
```
高度: 32px
背景: --color-surface-raised
边框: 1px solid --color-border
圆角: --radius-sm (4px)
内边距: 0 12px
文字: text-sm --color-text-primary
占位符: --color-text-muted

focus: border-color --color-primary, box-shadow: --shadow-focus
```

### 模态框 / 对话框
```
蒙层: rgba(0,0,0,0.6) backdrop
面板背景: --color-surface-overlay
边框: 1px solid --color-border
圆角: --radius-lg (8px)
阴影: --shadow-lg
内边距: 24px
标题: text-xl --color-text-primary
副标题/说明: text-sm --color-text-secondary
```

### 状态徽章（在线/离线 Pill）
```
在线: bg rgba(38,194,129,0.15), text #26C281, radius full, px:8 py:2, text-xs weight:500
离线: bg rgba(86,86,94,0.2),    text #56565E, radius full, px:8 py:2, text-xs weight:500
```

### 扫描进度条（ScanProgress）
```
轨道: bg --color-border, radius full, height 4px
进度: bg #F2C94C（扫描中黄色）, transition: width 300ms ease
完成后: bg #26C281 + 0.3s 延迟消失动画

状态文字: text-sm --color-text-secondary
设备计数: text-sm #F2C94C（扫描中）/ #26C281（完成）
```

### 摄像头播放器
```
容器: bg #000000, radius --radius-md
控制条: bg rgba(0,0,0,0.7), backdrop-filter: blur(8px)
边框: 1px solid --color-border
最大高度: 480px

无信号状态:
  bg: #0A0A0A
  图标: #56565E
  文字: text-sm --color-text-muted
```

### 通知 / Toast
```
容器: bg --color-surface-overlay, border 1px --color-border, radius --radius-md
阴影: --shadow-lg
最大宽度: 360px

类型:
  成功: 左边 3px 实线 #26C281
  错误: 左边 3px 实线 #F05252
  警告: 左边 3px 实线 #F07D38
  信息: 左边 3px 实线 #5E5CE6
```

### 表单（设置页 / 编辑对话框）
```
标签: text-sm --color-text-secondary, margin-bottom: 4px
输入框: 同上"输入框"规格
选择器: 同输入框，展开时 bg --color-surface-overlay
错误提示: text-xs #F05252, margin-top: 4px
表单组间距: 16px
```

---

## 8. 动效与过渡

```css
/* 微交互（hover、toggle） */
--duration-fast: 100ms;
--easing-fast: ease-out;

/* 状态变化（展开/收起、进度更新） */
--duration-base: 200ms;
--easing-base: cubic-bezier(0.16, 1, 0.3, 1);

/* 页面级过渡 */
--duration-slow: 300ms;
--easing-slow: cubic-bezier(0.4, 0, 0.2, 1);
```

**动效规则：**
- 列表行进入：`opacity 0→1 + translateY(4px→0)`，100ms，stagger 20ms
- 状态指示点（在线）：静态，无呼吸动画（避免视觉噪声）
- 扫描进度：`width` 过渡 300ms
- 模态框：`opacity + scale(0.96→1)` 200ms
- WebSocket 重连点：闪烁 `opacity 1→0.3` 1s infinite（仅重连时）

---

## 9. 设计护栏

**必须遵守：**
- 全局使用深色主题，不引入浅色背景页面（当前 MainLayout 的 `#f5f7fa` 需替换为 `--color-bg`）
- 所有颜色使用 CSS 变量，禁止在组件内硬编码 hex 值
- IP 地址、MAC 地址、文件名等机器标识符一律使用 mono 字体
- 状态色用于传达含义，不用于美化（绿色=在线，不是"好看"）
- Element Plus 组件通过 CSS 变量覆盖（不修改 element-plus 源码）

**禁止：**
- 不在深色页面上放置纯白（`#FFF`）大块背景
- 不使用大圆角（>8px）在列表项或表格行上
- 不用卡片网格布局展示设备列表主内容（用行列表，信息密度更高）
- 不添加纯装饰性动画（旋转、弹跳等）
- 不在没有操作意图的情况下堆叠多个模态框
- 不用颜色深浅表达层级（要用背景色 token 系统，不用 opacity 叠加）

---

## 附录：CSS 变量声明（根文件）

```css
/* 在 src/style.css 中添加 :root 声明 */
:root {
  /* 主色 */
  --color-primary:        #5E5CE6;
  --color-primary-hover:  #4E4CCF;
  --color-primary-subtle: rgba(94, 92, 230, 0.15);
  --color-primary-border: rgba(94, 92, 230, 0.35);

  /* 深色画布 */
  --color-bg:              #161618;
  --color-surface:         #1E1E20;
  --color-surface-raised:  #252528;
  --color-surface-overlay: #2C2C2F;
  --color-border:          #2F2F33;
  --color-border-subtle:   #28282B;

  /* 文字 */
  --color-text-primary:   #E8E8EC;
  --color-text-secondary: #8B8B96;
  --color-text-muted:     #56565E;
  --color-text-inverse:   #FFFFFF;

  /* 语义色 */
  --color-online:   #26C281;
  --color-offline:  #56565E;
  --color-error:    #F05252;
  --color-warning:  #F07D38;
  --color-scanning: #F2C94C;

  /* 设备类型色 */
  --color-type-camera:   #5E5CE6;
  --color-type-computer: #26C281;
  --color-type-phone:    #F2C94C;
  --color-type-iot:      #F07D38;
  --color-type-unknown:  #8B8B96;

  /* 圆角 */
  --radius-xs:   3px;
  --radius-sm:   4px;
  --radius-md:   6px;
  --radius-lg:   8px;
  --radius-full: 9999px;

  /* 阴影 */
  --shadow-sm:    0 1px 4px rgba(0, 0, 0, 0.5);
  --shadow-md:    0 4px 12px rgba(0, 0, 0, 0.6);
  --shadow-lg:    0 8px 24px rgba(0, 0, 0, 0.7);
  --shadow-focus: 0 0 0 2px rgba(94, 92, 230, 0.4);

  /* 动效 */
  --duration-fast: 100ms;
  --duration-base: 200ms;
  --duration-slow: 300ms;
  --easing-snap:   cubic-bezier(0.16, 1, 0.3, 1);

  /* 布局 */
  --sidebar-width:        220px;
  --sidebar-width-collapsed: 48px;
  --header-height:        56px;
  --content-max-width:    1400px;

  /* 字体 */
  --font-sans: "Inter", -apple-system, BlinkMacSystemFont,
               "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  --font-mono: "JetBrains Mono", "Fira Code", Consolas, monospace;
}
```
