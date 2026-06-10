// src/locales/zh-CN/charts.js
// i18n 键：图表组件的本地化文案（热力图、日历、BaseChart 等）
export default {
  empty: '暂无数据',
  weekdays: {
    0: '周日',
    1: '周一',
    2: '周二',
    3: '周三',
    4: '周四',
    5: '周五',
    6: '周六',
  },
  weekdayShort: {
    0: '日',
    1: '一',
    2: '二',
    3: '三',
    4: '四',
    5: '五',
    6: '六',
  },
  timeBands: {
    lateNight: '深夜',
    morning: '上午',
    afternoon: '下午',
    evening: '傍晚',
  },
  ranges: {
    today: '今日',
    last7d: '近7天',
    last30d: '近30天',
  },
  heatmap: {
    peakHour: '峰值时段',
    peakDay: '最活跃日',
    total: '总事件数',
    devicesOnline: '{count} 台在线',
    legendMax: '{count} 台',
    moreDevices: '+{count} 台…',
  },
  calendar: {
    monthsFormat: '{m}月',
    recordings: '{count} 条录像',
    minutes: ' · {count} 分钟',
    activeDays: '有录像天数',
    totalRecordings: '录像总数',
    peakDay: '峰值日 · {count} 条',
    legendLess: '少',
    legendMore: '多 · {count} 条/天',
  },
  size: {
    bytes: '{n} 字节',
    kb: '{n} KB',
    mb: '{n} MB',
    gb: '{n} GB',
    tb: '{n} TB',
  },
  duration: {
    short: '{m}:{s}',
  },
  date: {
    today: '今天',
    yesterday: '昨天',
    fallback: '{m}月{d}日',
  },
}
