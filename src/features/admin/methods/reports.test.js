import assert from 'node:assert/strict'
import test from 'node:test'
import reportsMethods from './reports.js'

test('report retry stops when the confirmation is cancelled', async () => {
  const confirmationOptions = []
  const context = {
    async confirmAction(options) {
      confirmationOptions.push(options)
      return false
    }
  }

  await reportsMethods.retryTask.call(context, { task_id: 'task-12' })

  assert.deepEqual(confirmationOptions, [{
    title: '确认重新生成报告',
    message: '确认重新生成这份报告？这会再次调用 AI 服务。',
    confirmButtonText: '确认重试'
  }])
})
