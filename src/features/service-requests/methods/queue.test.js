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

test('releasing a request closes the stale workspace after refreshing the queue', async t => {
  const previousAdapter = apiClient.defaults.adapter
  const previousSessionStorage = Object.getOwnPropertyDescriptor(globalThis, 'sessionStorage')
  const callOrder = []

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
    selectedRequest: { id: 26, status: 'reviewing' },
    workspace: { request: { id: 26 } },
    releaseSpecialty: 'psychology',
    releasing: false,
    releaseDialog: { visible: true, reason: ' 需要换人 ', error: '' },
    errorText: error => error.message,
    async loadRequests() {
      callOrder.push('loadRequests')
    },
    syncWorkspaceRoute(requestId) {
      callOrder.push(['syncWorkspaceRoute', requestId])
    },
    clearReportWorkspaceState() {
      callOrder.push('clearReportWorkspaceState')
      this.selectedRequest = null
      this.workspace = null
    }
  }

  await queueMethods.submitRelease.call(context)

  assert.deepEqual(callOrder, [
    'loadRequests',
    ['syncWorkspaceRoute', null],
    'clearReportWorkspaceState'
  ])
  assert.equal(context.selectedRequest, null)
  assert.equal(context.workspace, null)
  assert.equal(context.releasing, false)
  assert.equal(context.releaseDialog.visible, false)
})
