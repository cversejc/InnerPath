import assert from 'node:assert/strict'
import test from 'node:test'
import customerRequestMethods from './customer-requests.js'

test('withdrawing a request stops when the confirmation is cancelled', async () => {
  const confirmationOptions = []
  const request = { id: 18, status: 'submitted' }
  const context = {
    withdrawnId: null,
    requests: [request],
    canWithdraw: () => true,
    async confirmAction(options) {
      confirmationOptions.push(options)
      return false
    }
  }

  await customerRequestMethods.withdraw.call(context, request)

  assert.deepEqual(confirmationOptions, [{
    title: '确认撤回申请',
    message: '确定撤回这份申请吗？撤回后需要重新提交才能继续。',
    confirmButtonText: '确认撤回'
  }])
  assert.equal(context.withdrawnId, null)
  assert.deepEqual(context.requests, [request])
})
