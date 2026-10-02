import assert from 'node:assert/strict'
import test from 'node:test'
import { createConfirmAction } from './confirmAction.js'

test('confirm action applies the shared Vant dialog defaults and accepts confirmation', async () => {
  let dialogOptions
  const confirm = createConfirmAction(async options => {
    dialogOptions = options
    return 'confirm'
  })

  const accepted = await confirm({
    title: '确认发布日历',
    message: '发布后用户端将看到这版内容。',
    confirmButtonText: '确认发布'
  })

  assert.equal(accepted, true)
  assert.deepEqual(dialogOptions, {
    className: 'mobile-form-dialog',
    cancelButtonText: '取消',
    closeOnClickOverlay: false,
    messageAlign: 'left',
    title: '确认发布日历',
    message: '发布后用户端将看到这版内容。',
    confirmButtonText: '确认发布'
  })
})

test('confirm action returns false when the dialog is cancelled', async () => {
  const confirm = createConfirmAction(async () => {
    throw 'cancel'
  })

  assert.equal(await confirm({ title: '归档日历' }), false)
})

test('confirm action propagates dialog failures other than cancellation', async () => {
  const failure = new Error('dialog failed')
  const confirm = createConfirmAction(async () => {
    throw failure
  })

  await assert.rejects(confirm({ title: '重试报告' }), error => error === failure)
})
