import assert from 'node:assert/strict'
import test from 'node:test'
import apiClient from '../../../utils/apiClient.js'
import requestsMethods from './requests.js'

function deferred() {
  let resolve
  const promise = new Promise(done => { resolve = done })
  return { promise, resolve }
}

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

test('late request results cannot replace the currently selected request queue', async () => {
  const originalGet = apiClient.get
  const firstRequests = deferred()
  apiClient.get = async url => {
    if (url === '/admin/service-requests') return firstRequests.promise
    if (url === '/admin/calendar-requests') return { data: { total: 1, page: 1, size: 20, items: [{ id: 22 }] } }
    throw new Error(`unexpected request: ${url}`)
  }
  const context = {
    adminCalendarRequests: { total: 0, items: [] },
    adminServiceRequests: { total: 0, items: [] },
    calendarRequestFilters: { search: '', status: '', stalled_only: false, date_from: '', date_to: '' },
    cleanParams: params => params,
    errorText: error => error.message,
    message: '',
    requestFilters: { search: '', status: '', consultant_id: '', queue_filter: '', date_from: '', date_to: '' },
    requestKind: 'consultant',
    requestPage: 1,
    requestPageSize: 20,
    requestsLoading: false,
    requestsRequestId: 0
  }

  try {
    const firstLoad = requestsMethods.loadAdminRequests.call(context)
    context.requestKind = 'calendar'
    await requestsMethods.loadAdminRequests.call(context)
    firstRequests.resolve({ data: { total: 1, page: 1, size: 20, items: [{ id: 11 }] } })
    await firstLoad
  } finally {
    apiClient.get = originalGet
  }

  assert.deepEqual(context.adminCalendarRequests.items, [{ id: 22 }])
  assert.deepEqual(context.adminServiceRequests, { total: 0, items: [] })
  assert.equal(context.requestsLoading, false)
  assert.equal(context.message, '')
})

test('assignment completion does not reopen a report dialog after switching queues', async () => {
  const originalPatch = apiClient.patch
  const pendingSave = deferred()
  apiClient.patch = async () => pendingSave.promise
  const context = {
    activeTab: 'requests',
    adminServiceRequests: { items: [{ id: 42 }] },
    assignmentError: '',
    assignmentRequest: { id: 42 },
    assignmentSavingKey: '',
    async loadAdminRequests() {},
    message: '',
    requestKind: 'consultant',
    retryingRequestKey: '',
    errorText: error => error.message
  }

  try {
    const save = requestsMethods.assignAdminRequest.call(context, {
      requestId: 42,
      consultantId: 7,
      consultantType: 'mingli',
      mode: 'mingli'
    })
    context.requestKind = 'calendar'
    context.assignmentRequest = null
    pendingSave.resolve({ data: {} })
    await save
  } finally {
    apiClient.patch = originalPatch
  }

  assert.equal(context.assignmentRequest, null)
  assert.equal(context.message, '命理负责人已更新。')
  assert.equal(context.assignmentSavingKey, '')
})
