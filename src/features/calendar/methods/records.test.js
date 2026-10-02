import assert from 'node:assert/strict'
import test from 'node:test'

globalThis.sessionStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {}
}

const { default: recordsMethods } = await import('./records.js')

test('removing a decision log stops when the confirmation is cancelled', async () => {
  const confirmationOptions = []
  const record = { id: 42, content: '完成重要沟通' }
  const context = {
    confirmAction: async options => {
      confirmationOptions.push(options)
      return false
    },
    recordError: '',
    decisionLogs: [record],
    recordFeedback: ''
  }

  await recordsMethods.removeDecisionLog.call(context, record)

  assert.deepEqual(confirmationOptions, [{
    title: '删除行动记录',
    message: '确定删除这条记录吗？删除后不可恢复。',
    confirmButtonText: '删除记录'
  }])
  assert.deepEqual(context.decisionLogs, [record])
  assert.equal(context.recordError, '')
  assert.equal(context.recordFeedback, '')
})
