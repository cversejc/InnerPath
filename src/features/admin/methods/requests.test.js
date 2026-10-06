import assert from 'node:assert/strict'
import test from 'node:test'
import requestsMethods from './requests.js'

test('consultant workload link opens all report requests for that consultant', async () => {
  let loads = 0
  const context = {
    activeTab: 'staff',
    assignmentRequest: { id: 4 },
    requestFilters: { search: 'old', status: 'failed', consultant_id: '', queue_filter: 'stale_over_24h', date_from: '2026-01-01', date_to: '2026-01-31' },
    requestKind: 'calendar',
    requestPage: 7,
    loadAdminRequests: async () => { loads += 1 }
  }

  await requestsMethods.openConsultantServiceRequests.call(context, 23)

  assert.equal(context.activeTab, 'requests')
  assert.equal(context.assignmentRequest, null)
  assert.equal(context.requestKind, 'consultant')
  assert.equal(context.requestPage, 1)
  assert.deepEqual(context.requestFilters, {
    search: '',
    status: '',
    consultant_id: '23',
    queue_filter: '',
    date_from: '',
    date_to: ''
  })
  assert.equal(loads, 1)
})
