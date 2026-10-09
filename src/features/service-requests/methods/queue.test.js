import assert from 'node:assert/strict'
import test from 'node:test'
import apiClient from '../../../utils/apiClient.js'
import queueMethods from './queue.js'

test('accepting an available request switches to the assigned scope before loading its workspace', async t => {
  const previousAdapter = apiClient.defaults.adapter
  const previousSessionStorage = Object.getOwnPropertyDescriptor(globalThis, 'sessionStorage')
  const routeUpdates = []
  const workspaceLoads = []
  let requestListLoads = 0

  Object.defineProperty(globalThis, 'sessionStorage', {
    configurable: true,
    value: { getItem: () => null, setItem() {}, removeItem() {} }
  })
  apiClient.defaults.adapter = async config => ({
    data: {},
    status: 200,
    statusText: 'OK',
    headers: {},
    config
  })

  t.after(() => {
    apiClient.defaults.adapter = previousAdapter
    if (previousSessionStorage) Object.defineProperty(globalThis, 'sessionStorage', previousSessionStorage)
    else delete globalThis.sessionStorage
  })

  const context = {
    selectedRequest: { id: 24, status: 'submitted' },
    scope: 'available',
    admin: false,
    workspaceSection: 'overview',
    accepting: false,
    errorText: error => error.message,
    syncWorkspaceRoute: (...args) => routeUpdates.push(args),
    async loadRequests() {
      requestListLoads += 1
      assert.equal(this.scope, 'mine')
      this.selectedRequest = { id: 24, status: 'accepted', assigned_consultant_id: 9 }
    },
    async loadWorkspace(requestId) {
      workspaceLoads.push(requestId)
    }
  }

  await queueMethods.acceptRequest.call(context)

  assert.equal(requestListLoads, 1)
  assert.deepEqual(routeUpdates, [[24, 'overview']])
  assert.deepEqual(workspaceLoads, [24])
  assert.equal(context.accepting, false)
  assert.equal(context.message, '申请已接收，完整资料已开放。')
})

test('selecting a request adds a workbench history entry', async () => {
  const routeUpdates = []
  const context = {
    selectedRequest: null,
    workspaceSection: 'overview',
    stopPolling() {},
    syncWorkspaceRoute: (...args) => routeUpdates.push(args),
    $nextTick(callback) { callback() },
    $el: { scrollTo() {} },
    admin: false
  }

  await queueMethods.selectRequest.call(context, { id: 25, assigned_consultant_id: null })

  assert.deepEqual(routeUpdates, [[25, 'overview', { history: 'push' }]])
  assert.equal(context.selectedRequest.id, 25)
})

test('selecting another request clears the simplified workflow state', async () => {
  let resets = 0
  const context = {
    selectedRequest: null,
    selectedReportStepKey: 'S2',
    workspaceSection: 'overview',
    reportCase: { id: 41 },
    reportCaseContent: { evidence: [], findings: [], fragments: [] },
    reportCaseCompletionGate: {},
    reportAnalysisRuns: [{ id: 1 }],
    stopPolling() {},
    syncWorkspaceRoute() {},
    $nextTick(callback) { callback() },
    $el: { scrollTo() {} },
    admin: false,
    resetSimpleReportState() { resets += 1 }
  }

  await queueMethods.selectRequest.call(context, { id: 25, assigned_consultant_id: null })

  assert.equal(resets, 1)
  assert.equal(context.selectedReportStepKey, '')
  assert.equal(context.reportCase, null)
  assert.equal(context.reportAnalysisRuns.length, 0)
})

test('a selection that disappears from the queue clears the simplified workflow state', async t => {
  const previousAdapter = apiClient.defaults.adapter
  const previousStorage = Object.getOwnPropertyDescriptor(globalThis, 'sessionStorage')
  Object.defineProperty(globalThis, 'sessionStorage', { configurable: true, value: { getItem: () => null } })
  t.after(() => {
    apiClient.defaults.adapter = previousAdapter
    if (previousStorage) Object.defineProperty(globalThis, 'sessionStorage', previousStorage)
    else delete globalThis.sessionStorage
  })
  apiClient.defaults.adapter = async config => ({
    data: { items: [] },
    status: 200,
    statusText: 'OK',
    headers: {},
    config
  })

  let resets = 0
  const routeUpdates = []
  const context = {
    loading: false,
    requests: { items: [] },
    selectedRequest: { id: 24, status: 'accepted' },
    scope: 'mine',
    serviceType: '',
    statusFilter: '',
    workspace: { request: { id: 24 } },
    reportCase: { id: 41 },
    reportCaseContent: { evidence: [], findings: [], fragments: [] },
    reportCaseCompletionGate: {},
    errorText: error => error.message,
    syncWorkspaceRoute: (...args) => routeUpdates.push(args),
    stopPolling() {},
    resetSimpleReportState() { resets += 1 }
  }

  await queueMethods.loadRequests.call(context)

  assert.equal(resets, 1)
  assert.equal(context.selectedRequest, null)
  assert.equal(context.workspace, null)
  assert.equal(context.reportCase, null)
  assert.deepEqual(routeUpdates, [[null]])
})

test('a failed workspace load clears the simplified workflow state', async t => {
  const previousAdapter = apiClient.defaults.adapter
  const previousStorage = Object.getOwnPropertyDescriptor(globalThis, 'sessionStorage')
  Object.defineProperty(globalThis, 'sessionStorage', { configurable: true, value: { getItem: () => null } })
  t.after(() => {
    apiClient.defaults.adapter = previousAdapter
    if (previousStorage) Object.defineProperty(globalThis, 'sessionStorage', previousStorage)
    else delete globalThis.sessionStorage
  })
  apiClient.defaults.adapter = async () => { throw new Error('workspace unavailable') }

  let resets = 0
  const context = {
    loading: false,
    workspace: { request: { id: 24 } },
    reportCase: { id: 41 },
    reportCaseContent: { evidence: [], findings: [], fragments: [] },
    errorText: error => error.message,
    resetSimpleReportState() { resets += 1 }
  }

  await queueMethods.loadWorkspace.call(context, 24)

  assert.equal(resets, 1)
  assert.equal(context.workspace, null)
  assert.equal(context.message, 'workspace unavailable')
  assert.equal(context.loading, false)
})
