import assert from 'node:assert/strict'
import test from 'node:test'
import apiClient from '../../../utils/apiClient.js'
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

test('report supplement submits trimmed answers and reloads the request list', async () => {
  const originalPost = apiClient.post
  const calls = []
  apiClient.post = async (url, payload) => {
    calls.push({ url, payload })
    return { data: { status: 'accepted' } }
  }
  const context = {
    followUpAnswers: { 18: '  具体情况补充  ' },
    followUpResponseKeys: {},
    supplementSubmittingId: null,
    message: '',
    messageType: 'info',
    async loadRequests() { this.refreshed = true },
    errorText: error => error.message
  }

  try {
    await customerRequestMethods.submitReportSupplement.call(context, {
      id: 18,
      report_case_id: 72,
      service_type: 'report'
    })
  } finally {
    apiClient.post = originalPost
  }

  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, '/report-cases/72/supplements')
  assert.equal(calls[0].payload.answer, '具体情况补充')
  assert.match(calls[0].payload.response_key, /^report-follow-up-18-/)
  assert.equal(context.followUpAnswers[18], '')
  assert.deepEqual(context.followUpResponseKeys, {})
  assert.equal(context.refreshed, true)
  assert.equal(context.message, '补充资料已提交，咨询师会继续审核当前节点。')
  assert.equal(context.supplementSubmittingId, null)
})

test('report supplement retries reuse the same response key after a network error', async () => {
  const originalPost = apiClient.post
  const calls = []
  apiClient.post = async (url, payload) => {
    calls.push(payload)
    if (calls.length === 1) throw new Error('network unavailable')
    return { data: { status: 'accepted' } }
  }
  const context = {
    followUpAnswers: { 19: '补充事实' },
    followUpResponseKeys: {},
    supplementSubmittingId: null,
    message: '',
    messageType: 'info',
    async loadRequests() {},
    errorText: error => error.message
  }
  const item = { id: 19, report_case_id: 73, service_type: 'report' }

  try {
    await customerRequestMethods.submitReportSupplement.call(context, item)
    const firstKey = context.followUpResponseKeys[19].key
    await customerRequestMethods.submitReportSupplement.call(context, item)
    assert.equal(calls[0].response_key, firstKey)
    assert.equal(calls[1].response_key, firstKey)
    assert.equal(context.message, '补充资料已提交，咨询师会继续审核当前节点。')
  } finally {
    apiClient.post = originalPost
  }
})
