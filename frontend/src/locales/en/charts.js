// src/locales/en/charts.js
// i18n keys: chart component localization (heatmap, calendar, BaseChart, etc.)
export default {
  empty: 'No data',
  weekdays: {
    0: 'Sun',
    1: 'Mon',
    2: 'Tue',
    3: 'Wed',
    4: 'Thu',
    5: 'Fri',
    6: 'Sat',
  },
  // Calendar heatmap only renders Sun/Tue/Thu/Sat rows
  weekdayShort: {
    0: 'Sun',
    2: 'Tue',
    4: 'Thu',
    6: 'Sat',
  },
  timeBands: {
    lateNight: 'Late Night',
    morning: 'Morning',
    afternoon: 'Afternoon',
    evening: 'Evening',
  },
  ranges: {
    today: 'Today',
    last7d: 'Last 7 days',
    last30d: 'Last 30 days',
  },
  heatmap: {
    peakHour: 'Peak hour',
    peakDay: 'Most active day',
    total: 'Total events',
    devicesOnline: '{count} online',
    legendMax: '{count}',
    moreDevices: '+{count} more…',
  },
  calendar: {
    monthsFormat: '{m}',
    recordings: '{count} recordings',
    minutes: ' · {count} min',
  },
  size: {
    bytes: '{n} B',
    kb: '{n} KB',
    mb: '{n} MB',
    gb: '{n} GB',
    tb: '{n} TB',
  },
  duration: {
    short: '{m}:{s}',
  },
  date: {
    today: 'Today',
    yesterday: 'Yesterday',
    fallback: '{m}/{d}',
  },
}
