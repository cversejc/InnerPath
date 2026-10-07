import assert from 'node:assert/strict'
import test from 'node:test'

globalThis.sessionStorage ||= {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {}
}

const { default: navigationMethods } = await import('./navigation.js')

function createContext() {
  const loaded = []
  return {
    activeTab: 'overview',
    activeLoads: loaded,
    autoRefresh: false,
    calendarUsers: [],
    requestKind: 'consultant',
    requestFilters: {},
    calendarRequestFilters: {},
    requestPage: 4,
    reportSection: 'reports',
    taskFilters: {},
    taskPage: 3,
    syncAutoRefresh() {},
    async loadAdminRequests() { loaded.push('requests') },
    async loadReportTasks() { loaded.push('tasks') },
    async loadReports() { loaded.push('reports') },
    ...navigationMethods
  }
}

test('assignment alerts open the request list with the matching queue filter', async () => {
  const context = createContext()

  await navigationMethods.goFromAlert.call(context, {
    key: 'incomplete_assignment_over_24h',
    route: 'requests'
  })

  assert.equal(context.activeTab, 'requests')
  assert.equal(context.requestPage, 1)
  assert.equal(context.requestKind, 'consultant')
  assert.equal(context.requestFilters.queue_filter, 'incomplete_assignment_over_24h')
  assert.equal(context.activeLoads.at(-1), 'requests')
})

test('stalled calendar alerts open the generating requests filter', async () => {
  const context = createContext()

  await navigationMethods.goFromAlert.call(context, {
    key: 'stalled_calendar_requests',
    route: 'requests'
  })

  assert.equal(context.requestKind, 'calendar')
  assert.equal(context.calendarRequestFilters.status, '')
  assert.equal(context.calendarRequestFilters.stalled_only, true)
  assert.equal(context.activeLoads.at(-1), 'requests')
})

test('legacy report failure alerts open the read-only failed task list', async () => {
  const context = createContext()

  await navigationMethods.goFromAlert.call(context, {
    key: 'failed_reports',
    route: 'reports'
  })

  assert.equal(context.activeTab, 'reports')
  assert.equal(context.reportSection, 'tasks')
  assert.equal(context.taskFilters.status, 'failed')
  assert.equal(context.activeLoads.at(-1), 'tasks')
})

test('report workflow alerts open the matching operational queue', async () => {
  const context = createContext()

  await navigationMethods.goFromAlert.call(context, {
    key: 'workflow_attention',
    route: 'requests'
  })

  assert.equal(context.requestKind, 'consultant')
  assert.equal(context.requestFilters.queue_filter, 'workflow_attention')
  assert.equal(context.activeLoads.at(-1), 'requests')
})

test('opening an exceptional request passes its id to the staff workbench', async () => {
  let destination
  await navigationMethods.openReportWorkflow.call({
    $router: { push: value => { destination = value } }
  }, { id: 37 })

  assert.deepEqual(destination, {
    path: '/staff',
    query: { scope: 'all', request_id: '37', section: 'overview' }
  })
})
