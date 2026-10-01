import { formatShortDate } from './formatters.js'

const CHART_GRID_LINES = [18, 67, 116, 165, 214]
const TREND_SERIES = [
  { key: 'new_users', label: '新增用户', color: '#b85c50' },
  { key: 'reports', label: '报告', color: 'var(--gold-deep, #8b5a14)' },
  { key: 'decision_logs', label: '行动记录', color: '#59483d' }
]

export function createDashboardViewModel(dashboard) {
  const metrics = dashboard?.metrics || {}
  const trends = dashboard?.trends || []
  const distributions = dashboard?.distributions || {}
  const trendMax = Math.max(...trends.flatMap(item => [item.new_users, item.reports, item.decision_logs]), 1)
  const trendSeries = TREND_SERIES.map(item => ({
    ...item,
    points: trends.map((point, index) => {
      const x = 28 + (index * 708 / Math.max(1, trends.length - 1))
      const y = 214 - ((point[item.key] || 0) / trendMax) * 196
      return `${x.toFixed(1)},${y.toFixed(1)}`
    }).join(' ')
  }))
  const tickStep = Math.max(1, Math.ceil(trends.length / 6))
  const trendTicks = trends
    .map((point, index) => ({
      index,
      x: 28 + (index * 708 / Math.max(1, trends.length - 1)),
      label: formatShortDate(point.date)
    }))
    .filter((tick, index) => index % tickStep === 0 || index === trends.length - 1)

  return {
    metricCards: [
      { key: 'users', label: '用户总数', value: metrics.user_total ?? 0, caption: `活跃 ${metrics.active_users ?? 0} · 本期新增 ${metrics.new_users ?? 0}`, mark: '人', tone: 'cinnabar' },
      { key: 'reports', label: '报告总数', value: metrics.report_total ?? 0, caption: `成功率 ${metrics.report_success_rate ?? 0}%`, mark: '笺', tone: 'gold' },
      { key: 'tasks', label: '报告任务', value: metrics.report_processing ?? 0, caption: `生成中 · 失败 ${metrics.report_failed ?? 0}`, mark: 'AI', tone: 'ink' },
      { key: 'calendars', label: '已发布日历', value: metrics.published_calendars ?? 0, caption: `用户行动记录 ${metrics.decision_logs ?? 0}`, mark: '历', tone: 'jade' }
    ],
    chartGridLines: [...CHART_GRID_LINES],
    distributionGroups: [
      { key: 'roles', label: '用户角色', items: distributions.users_by_role || [] },
      { key: 'reports', label: '报告状态', items: distributions.reports_by_status || [] },
      { key: 'calendars', label: '日历状态', items: distributions.calendars_by_status || [] }
    ],
    trendSeries,
    trendTicks
  }
}
