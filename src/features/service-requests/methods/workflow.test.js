import assert from 'node:assert/strict'
import test from 'node:test'
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
