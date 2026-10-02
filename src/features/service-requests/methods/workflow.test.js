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
