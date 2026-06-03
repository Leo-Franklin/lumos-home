# 设备活跃热力图增强 & 数据分析页面设计

**日期**: 2026-04-29  
**状态**: 已批准

---

## 概述

本设计涵盖两个相关功能：

1. **热力图组件化增强** — 将 `DevicesView.vue` 中现有的 D3 热力图提取为可复用的 `HeatmapChart.vue` 组件，并增加设备类型筛选、更丰富的 tooltip 和 24h 视图。
2. **数据分析页面** — 新建 `AnalyticsView.vue`，采用信息流布局，包含 8 张图表，提供全面的家庭网络洞察。

技术栈：Vue 3 Composition API、D3.js v7、Element Plus、Pinia、Axios。

---

## 架构

### 文件结构

```
src/
├── components/
│   └── charts/
│       ├── BaseChart.vue          # 通用容器：标题、加载态、空态、时间范围选择器
│       ├── HeatmapChart.vue       # 设备活跃时段热力图（从 DevicesView 提取并增强）
│       ├── LineChart.vue          # 折线/面积图
│       ├── BarChart.vue           # 柱状图（水平 & 垂直）
│       ├── DonutChart.vue         # 环形图
│       └── CalendarHeatmap.vue    # 日历热力图（类 GitHub 贡献图）
├── views/
│   ├── DevicesView.vue            # 热力图改为引用 HeatmapChart.vue
│   ├── DashboardView.vue          # 新增 3 个摘要 mini-chart
│   └── AnalyticsView.vue          # 新建，组装全部 8 张图表
├── api/
│   └── analytics.js               # 新建，分析专用 API 层
└── router/index.js                # 新增 /analytics 路由
```

### 数据流

```
AnalyticsView
  └── analytics.js (API 层)
       └── 各 XxxChart 组件（props 传入数据）
            └── D3 渲染（组件内管理 D3 生命周期，watch 数据变化触发重绘）
```

每个图表组件通过 `props` 接收数据，通过 `emit` 向上传递交互事件（如筛选变化）。`BaseChart.vue` 统一处理加载中、空数据、时间范围切换等通用状态。

---

## 功能一：热力图组件（HeatmapChart.vue）

### 现有实现（DevicesView.vue:74-146）
- D3.js 渲染，支持 7d / 30d 范围切换
- 单一颜色梯度，无筛选

### 增强点

| 维度 | 现有 | 增强后 |
|------|------|--------|
| 时间范围 | 7d / 30d | 新增 24h（今日细粒度，x 轴为小时，y 轴为分钟段） |
| 颜色 | 固定紫色梯度 | 随设备类型筛选切换对应颜色主题 |
| Tooltip | 显示在线数量 | 显示时段、在线设备数、设备名称列表（最多 5 条） |
| 筛选 | 无 | 设备类型多选：camera / phone / computer / IoT / unknown |
| 复用性 | 内嵌于 DevicesView | 独立组件，props 驱动，可在 Analytics 页复用 |

### 组件接口

```vue
<!-- Props -->
// 7d/30d 模式：day 为 'YYYY-MM-DD'，hour 为 0-23
// 24h 模式：day 为空字符串，hour 为 0-23，minuteBlock 为 0-5（每 10 分钟一格）
data: Array<{ day: string, hour: number, minuteBlock?: number, count: number, devices: string[] }>
range: '24h' | '7d' | '30d'  (default: '7d')
deviceTypes: string[]         (default: [] 表示全部)
height: number                (default: 200)

<!-- Emits -->
@range-change="(range) => {}"
@type-filter-change="(types) => {}"
@cell-click="({ day, hour, devices }) => {}"
```

### API 变更

`GET /devices/heatmap?range=7d&device_type=camera,phone` — 现有接口增加可选 `device_type` 过滤参数。

---

## 功能二：数据分析页面（AnalyticsView.vue）

### 路由

```
/analytics  →  AnalyticsView.vue
侧边栏新增"数据分析"菜单项，图标：DataAnalysis（Element Plus Icons）
```

### 页面布局（信息流，从宏观到细节）

```
┌─────────────────────────────────────────────┐
│  ① 设备活跃时段热力图（全宽）               │
└─────────────────────────────────────────────┘
┌──────────────────────┐ ┌──────────────────────┐
│ ③ 在线设备数量趋势   │ │ ⑤ 录像活动日历热力图 │
└──────────────────────┘ └──────────────────────┘
┌──────────┐ ┌──────────┐ ┌──────────────────────┐
│ ② 设备   │ │ ⑥ 新设备 │ │ ⑧ 各类型活跃时段对比 │
│ 类型分布 │ │ 发现趋势 │ │                      │
└──────────┘ └──────────┘ └──────────────────────┘
┌──────────────────────┐ ┌──────────────────────┐
│ ④ 设备响应时延分布   │ │ ⑦ 设备在线稳定性排行 │
└──────────────────────┘ └──────────────────────┘
```

### 图表清单

| # | 图表 | 组件 | 描述 |
|---|------|------|------|
| ① | 设备活跃时段热力图 | `HeatmapChart` | hour×day 网格，支持类型筛选，全宽置顶 |
| ② | 设备类型分布 | `DonutChart` | 各类型设备数量占比，点击扇区高亮 |
| ③ | 在线设备数量趋势 | `LineChart` | 每小时在线总数折线面积图，7d/30d |
| ④ | 设备响应时延分布 | `BarChart` (水平) | 各设备平均延迟，颜色阈值：绿色 <50ms、黄色 50-200ms、橙色 >200ms |
| ⑤ | 录像活动日历热力图 | `CalendarHeatmap` | 类 GitHub 贡献图，每格一天 |
| ⑥ | 新设备发现趋势 | `BarChart` (垂直) | 每周新发现设备数；某周数量超过过去 4 周均值 2 倍时柱体高亮为橙色 |
| ⑦ | 设备在线稳定性排行 | `BarChart` (水平) | 各设备在线率%，颜色分级：绿色 ≥90%、黄色 70-89%、橙色 <70% |
| ⑧ | 各类型活跃时段对比 | `BarChart` (分组) | 横轴 24 小时，各类型设备分组柱状 |

---

## 新增后端 API

| 接口 | 用途 | 图表 |
|------|------|------|
| `GET /analytics/online-trend?range=7d\|30d` | 每小时在线设备数时序 | ③ |
| `GET /analytics/device-type-stats` | 各类型设备数量 | ② |
| `GET /analytics/response-time` | 各设备平均响应时延（ms） | ④ |
| `GET /analytics/recording-calendar?range=90d` | 每日录像数量与总时长 | ⑤ |
| `GET /analytics/new-devices?range=90d&group_by=week\|month` | 每周/月新发现设备数 | ⑥ |
| `GET /analytics/device-stability?range=7d\|30d` | 各设备在线率与趋势 | ⑦ |
| `GET /analytics/type-activity?range=7d` | 每小时各设备类型在线数 | ⑧ |
| `GET /devices/heatmap` | 现有接口，增加 `device_type` 参数 | ① |

所有接口返回 JSON，由 `src/api/analytics.js` 统一封装。

---

## Dashboard 摘要增强

在现有 `DashboardView.vue` 统计卡下方新增一排迷你图：

- **在线趋势 sparkline**：过去 24h 在线设备数折线（`LineChart`，mini 尺寸）
- **7 日录像量**：7 日柱状图（`BarChart`，mini 尺寸）
- **设备类型小环形图**：`DonutChart`，mini 尺寸，无图例

这三个迷你图复用 Analytics 页的图表组件，复用相同 API。

---

## 错误处理与边界情况

- 所有图表组件在 `BaseChart.vue` 层统一处理：加载中骨架屏、接口报错提示、数据为空的空态插图。
- 时间范围切换时显示加载态，防止旧数据闪烁。
- D3 图表在组件 `onUnmounted` 时清理事件监听器和 tooltip DOM。
- 响应式：图表在窗口 resize 时重新计算宽度并重绘（`ResizeObserver`）。

---

## 不在范围内

- 实时 WebSocket 推送（Analytics 页轮询即可，30s 刷新）
- 数据导出（CSV / PNG）
- 自定义时间范围选择器（仅预设范围）
- 移动端适配优化
