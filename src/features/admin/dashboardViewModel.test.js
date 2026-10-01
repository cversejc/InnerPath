import assert from 'node:assert/strict'
import test from 'node:test'
import { createDashboardViewModel } from './dashboardViewModel.js'

test('admin dashboard view model supplies empty defaults', () => {
  const viewModel = createDashboardViewModel(null)

  assert.deepEqual(viewModel.metricCards.map(({ key, value }) => ({ key, value })), [
    { key: 'users', value: 0 },
    { key: 'reports', value: 0 },
    { key: 'tasks', value: 0 },
    { key: 'calendars', value: 0 }
  ])
  assert.deepEqual(viewModel.chartGridLines, [18, 67, 116, 165, 214])
  assert.deepEqual(viewModel.trendSeries.map(({ points }) => points), ['', '', ''])
  assert.deepEqual(viewModel.trendTicks, [])
  assert.deepEqual(viewModel.distributionGroups.map(({ items }) => items), [[], [], []])
})

test('admin dashboard view model maps metrics, chart coordinates, and distributions', () => {
  const viewModel = createDashboardViewModel({
    metrics: {
      user_total: 5,
      active_users: 3,
      new_users: 2,
      report_total: 8,
      report_success_rate: 75,
      report_processing: 1,
      report_failed: 2,
      published_calendars: 4,
      decision_logs: 9
    },
    trends: [
      { date: '2026-10-01', new_users: 2, reports: 4, decision_logs: 10 },
      { date: '2026-10-02', new_users: 6, reports: 5, decision_logs: 0 }
    ],
    distributions: {
      users_by_role: [{ label: '用户', value: 5 }],
      reports_by_status: [{ label: '已完成', value: 8 }],
      calendars_by_status: [{ label: '已发布', value: 4 }]
    }
  })

  assert.equal(viewModel.metricCards[0].caption, '活跃 3 · 本期新增 2')
  assert.equal(viewModel.metricCards[1].caption, '成功率 75%')
  assert.deepEqual(viewModel.trendSeries.map(({ key, points }) => ({ key, points })), [
    { key: 'new_users', points: '28.0,174.8 736.0,96.4' },
    { key: 'reports', points: '28.0,135.6 736.0,116.0' },
    { key: 'decision_logs', points: '28.0,18.0 736.0,214.0' }
  ])
  assert.deepEqual(viewModel.trendTicks, [
    { index: 0, x: 28, label: '10/01' },
    { index: 1, x: 736, label: '10/02' }
  ])
  assert.deepEqual(viewModel.distributionGroups.map(({ key, items }) => ({ key, items })), [
    { key: 'roles', items: [{ label: '用户', value: 5 }] },
    { key: 'reports', items: [{ label: '已完成', value: 8 }] },
    { key: 'calendars', items: [{ label: '已发布', value: 4 }] }
  ])
})

test('admin dashboard view model samples trend ticks and keeps the final date', () => {
  const trends = Array.from({ length: 10 }, (_, index) => ({
    date: `2026-10-${String(index + 1).padStart(2, '0')}`,
    new_users: index,
    reports: index,
    decision_logs: index
  }))
  const viewModel = createDashboardViewModel({ trends })

  assert.deepEqual(viewModel.trendTicks.map(({ index }) => index), [0, 2, 4, 6, 8, 9])
})
