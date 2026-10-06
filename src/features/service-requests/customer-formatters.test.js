import assert from 'node:assert/strict'
import test from 'node:test'
import {
  canWithdrawServiceRequest,
  customerServiceRequestStatusLabel,
  customerServiceTypeLabel,
  serviceRequestEditPath,
  topicLabel
} from './customer-formatters.js'

test('customer request formatters keep customer-facing status and type labels', () => {
  assert.equal(customerServiceRequestStatusLabel('submitted'), '等待咨询师接单')
  assert.equal(customerServiceRequestStatusLabel('needs_info'), '需要补充资料')
  assert.equal(customerServiceRequestStatusLabel('future_status'), 'future_status')
  assert.equal(customerServiceTypeLabel('calendar'), '决策日历申请')
  assert.equal(customerServiceTypeLabel('report'), '报告申请')
})

test('customer request formatters reuse topic labels and build edit routes', () => {
  assert.equal(topicLabel(['career', 'family']), '职业发展、家庭议题')
  assert.equal(serviceRequestEditPath({ service_type: 'report', id: 12 }), '/pages/assessment/assessment?requestId=12')
  assert.equal(serviceRequestEditPath({ service_type: 'report', id: 13, report_case_id: 72 }), '/pages/requests/requests#request-13-supplement')
  assert.equal(serviceRequestEditPath({ service_type: 'calendar', id: 18 }), '/pages/calendar/calendar?generate=1')
})

test('only submitted and information-needed requests can be withdrawn', () => {
  assert.equal(canWithdrawServiceRequest('submitted'), true)
  assert.equal(canWithdrawServiceRequest('needs_info'), true)
  assert.equal(canWithdrawServiceRequest('accepted'), false)
  assert.equal(canWithdrawServiceRequest('delivered'), false)
})
