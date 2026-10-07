import assert from 'node:assert/strict'
import test from 'node:test'
import apiClient from '../../../utils/apiClient.js'
import dashboardMethods from './dashboard.js'

function deferred() {
  let resolve
  const promise = new Promise(done => { resolve = done })
  return { promise, resolve }
}

function dashboardContext(range = '7d') {
  return {
    dashboard: null,
    dashboardLoadError: false,
    dashboardLoading: false,
    dashboardRange: range,
    dashboardRequestId: 0,
    dashboardRequestInFlight: false,
    lastUpdated: ''
  }
}

test('late dashboard responses cannot replace the latest selected range', async () => {
  const originalGet = apiClient.get
  const firstDashboard = deferred()
  apiClient.get = async (url, options) => {
    if (url !== '/admin/dashboard/overview') throw new Error(`unexpected request: ${url}`)
    if (options.params.range === '7d') return firstDashboard.promise
    return { data: { range_preset: '30d' } }
  }
  const context = dashboardContext()

  try {
    const firstLoad = dashboardMethods.loadDashboard.call(context)
    context.dashboardRange = '30d'
    await dashboardMethods.loadDashboard.call(context)
    firstDashboard.resolve({ data: { range_preset: '7d' } })
    await firstLoad
  } finally {
    apiClient.get = originalGet
  }

  assert.deepEqual(context.dashboard, { range_preset: '30d' })
  assert.equal(context.dashboardLoading, false)
  assert.equal(context.dashboardRequestInFlight, false)
  assert.equal(context.dashboardLoadError, false)
  assert.ok(context.lastUpdated)
})

test('automatic dashboard refresh skips a request while another refresh is in flight', async () => {
  const originalGet = apiClient.get
  const pendingDashboard = deferred()
  let calls = 0
  apiClient.get = async () => {
    calls += 1
    return pendingDashboard.promise
  }
  const context = dashboardContext('30d')

  try {
    const firstLoad = dashboardMethods.loadDashboard.call(context, true)
    await dashboardMethods.loadDashboard.call(context, true)
    pendingDashboard.resolve({ data: { range_preset: '30d' } })
    await firstLoad
  } finally {
    apiClient.get = originalGet
  }

  assert.equal(calls, 1)
  assert.equal(context.dashboard.range_preset, '30d')
  assert.equal(context.dashboardRequestInFlight, false)
  assert.equal(context.dashboardLoading, false)
})
