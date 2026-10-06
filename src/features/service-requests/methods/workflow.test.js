import assert from 'node:assert/strict'
import test from 'node:test'
import apiClient from '../../../utils/apiClient.js'
import workflowMethods from './workflow.js'

test('reject request opens an editable reason dialog for an admin', () => {
  const context = {
    admin: true,
    workspace: { request: { id: 7 } },
    rejectSaving: false,
    rejectDialog: { visible: false, reason: '', error: '' }
  }

  workflowMethods.rejectRequest.call(context)

  assert.equal(context.rejectDialog.visible, true)
  assert.equal(context.rejectDialog.reason, '当前申请暂不具备处理条件')
  assert.equal(context.rejectDialog.error, '')
})

test('reject request does not open for a consultant without admin access', () => {
  const context = {
    admin: false,
    workspace: { request: { id: 7 } },
    rejectSaving: false,
    rejectDialog: { visible: false, reason: '', error: '' }
  }

  workflowMethods.rejectRequest.call(context)

  assert.equal(context.rejectDialog.visible, false)
})

test('reject request requires a non-empty reason before calling the API', async () => {
  const context = {
    admin: true,
    workspace: { request: { id: 7 } },
    rejectSaving: false,
    rejectDialog: { visible: true, reason: '  ', error: '' }
  }

  await workflowMethods.submitReject.call(context)

  assert.equal(context.rejectDialog.error, '请输入关闭原因')
  assert.equal(context.rejectSaving, false)
})

test('regenerate AI requires confirmation before saving a snapshot and retrying', async () => {
  const confirmationOptions = []
  const context = {
    workspace: { request: { id: 7 } },
    aiStarting: false,
    async confirmAction(options) {
      confirmationOptions.push(options)
      return false
    }
  }

  await workflowMethods.regenerateAI.call(context)

  assert.deepEqual(confirmationOptions, [{
    title: '确认重新生成 AI 初稿',
    message: '重新生成前会保存当前咨询师修改的版本快照。确定继续吗？',
    confirmButtonText: '保存并重新生成'
  }])
  assert.equal(context.aiStarting, false)
})

test('delivery requires confirmation before changing the request to read-only', async () => {
  const confirmationOptions = []
  const context = {
    workspace: { request: { id: 7, status: 'reviewing' } },
    delivering: false,
    async confirmAction(options) {
      confirmationOptions.push(options)
      return false
    }
  }

  await workflowMethods.deliver.call(context)

  assert.deepEqual(confirmationOptions, [{
    title: '确认交付给用户',
    message: '确认已完成人工审校并交付给用户吗？交付后申请和结果将进入只读状态。',
    confirmButtonText: '确认交付'
  }])
  assert.equal(context.delivering, false)
  assert.equal(context.workspace.request.status, 'reviewing')
})

test('report case follow-up questions are tied to the current report node', async () => {
  const originalPost = apiClient.post
  const calls = []
  apiClient.post = async (url, payload) => {
    calls.push({ url, payload })
    return { data: { status: 'needs_info', needs_info_reason: payload.reason } }
  }
  const context = {
    workspace: { request: { id: 7, service_type: 'report' } },
    reportCase: { id: 31 },
    infoStepKey: 'S2',
    infoReason: '  核对这段经历的具体时间  ',
    infoSaving: false,
    showInfoPanel: true,
    message: '',
    errorText: error => error.message,
    async loadWorkspace(id) { this.workspaceReloaded = id },
    async loadRequests() { this.requestsReloaded = true }
  }

  try {
    await workflowMethods.requestInfo.call(context)
  } finally {
    apiClient.post = originalPost
  }

  assert.deepEqual(calls, [{
    url: '/report-cases/31/steps/S2/request-info',
    payload: { reason: '核对这段经历的具体时间' }
  }])
  assert.equal(context.workspace.request.status, 'needs_info')
  assert.equal(context.workspaceReloaded, 7)
  assert.equal(context.requestsReloaded, true)
  assert.equal(context.showInfoPanel, false)
  assert.equal(context.infoStepKey, '')
  assert.equal(context.message, '已向用户发送补充问题，当前审核节点会在收到回复后恢复。')
})
