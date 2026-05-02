// src/locales/zh-CN/schedule.js
export default {
  // CronSelector (already exists in plan, adding ScheduleView keys here)
  // Cron presets
  presetDaily2am: '每天凌晨 2:00',
  presetWeekday8am: '工作日早 8:00',
  presetDaily10pm: '每天晚上 22:00',
  presetEvery30min: '每 30 分钟',
  presetWeekendMidnight: '周末凌晨',
  presetHourly: '每小时整点',
  // Cron tabs
  tabPreset: '快速选择',
  tabCustom: '自定义时间',
  tabAdvanced: '高级 (Cron)',
  // Cron descriptions
  cronNotSet: '未设置',
  cronEveryMinute: '每分钟触发',
  cronEveryNMinute: '每 {n} 分钟触发',
  cronHourlyAt: '每小时第 {min} 分触发',
  cronDaily: '每天 {time} 触发',
  cronWeekday: '工作日 {time} 触发',
  cronWeekend: '周末 {time} 触发',
  cronCustom: '自定义：{expr}',
  // Weekday labels
  weekdayShort: { 1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 0: '日' },
  // UI
  triggerTime: '触发时间',
  weekday: '星期（全选 = 每天）',
  advPlaceholder: '分 时 日 月 周，如 0 2 * * *',
  advHint: '格式：分 小时 日 月 周几',
  trigger: '触发',
  // ScheduleView keys
  title: '录制计划',
  newSchedule: '新建计划',
  editSchedule: '编辑计划',
  scheduleName: '计划名称',
  cameraMac: '摄像头 MAC',
  cronExpr: 'Cron 表达式',
  segmentDuration: '分段时长',
  segmentUnit: ' 分钟',
  status: '状态',
  actions: '操作',
  selectCamera: '选择摄像头',
  namePlaceholder: '如：夜间录制',
  segmentLabel: '分段时长(秒)',
  enabled: '是否启用',
  unnamed: '(未命名)',
  deleteConfirm: '确定删除计划「{name}」？',
  updated: '已更新',
  created: '已创建',
  deleted: '已删除',
  // ScheduleView messages
  cancel: '取消',
}
