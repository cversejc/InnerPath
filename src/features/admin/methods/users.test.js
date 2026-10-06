import assert from 'node:assert/strict'
import test from 'node:test'
import apiClient from '../../../utils/apiClient.js'
import usersMethods from './users.js'

test('password reset opens a dialog for an active account', async () => {
  const context = {
    passwordDialog: { visible: false, user: null, password: '', showPassword: false, error: '', submitting: false }
  }

  await usersMethods.resetUserPassword.call(context, { id: 12, name: '测试用户', is_active: true })

  assert.equal(context.passwordDialog.visible, true)
  assert.equal(context.passwordDialog.user.id, 12)
  assert.equal(context.passwordDialog.password, '')
})

test('password reset rejects a short password before submitting', async () => {
  const context = {
    passwordDialog: {
      visible: true,
      user: { id: 12 },
      password: 'short7',
      showPassword: false,
      error: '',
      submitting: false
    }
  }

  await usersMethods.submitPasswordReset.call(context)

  assert.equal(context.passwordDialog.error, '新密码至少需要 8 位')
  assert.equal(context.passwordDialog.submitting, false)
})

test('inactive users follow the existing enable-account action', async () => {
  const user = { id: 13, is_active: false }
  let toggledUser = null
  const context = {
    passwordDialog: { visible: false, user: null, password: '', showPassword: false, error: '', submitting: false },
    async toggleUser(value) { toggledUser = value }
  }

  await usersMethods.resetUserPassword.call(context, user)

  assert.equal(toggledUser, user)
  assert.equal(context.passwordDialog.visible, false)
})

test('closing the password dialog clears sensitive input', () => {
  const context = {
    passwordDialog: {
      visible: false,
      user: { id: 12 },
      password: 'sensitive-value',
      showPassword: true,
      error: 'error',
      submitting: false
    }
  }

  usersMethods.clearPasswordDialog.call(context, false)

  assert.equal(context.passwordDialog.user, null)
  assert.equal(context.passwordDialog.password, '')
  assert.equal(context.passwordDialog.showPassword, false)
  assert.equal(context.passwordDialog.error, '')
})

test('consultant workload period changes fetch read-only metrics and update the selected range', async () => {
  const originalGet = apiClient.get
  const calls = []
  apiClient.get = async (url, options) => {
    calls.push({ url, params: options.params })
    return { data: { period_days: options.params.period_days, items: [{ consultant_id: 4 }] } }
  }
  const context = {
    consultantWorkloadLoading: false,
    consultantWorkloadError: '',
    consultantWorkloads: [],
    consultantWorkloadPeriodDays: 30,
    errorText: error => error.message
  }

  try {
    await usersMethods.changeConsultantWorkloadPeriod.call(context, 7)
  } finally {
    apiClient.get = originalGet
  }

  assert.deepEqual(calls, [{ url: '/admin/consultants/workload', params: { period_days: 7 } }])
  assert.equal(context.consultantWorkloadPeriodDays, 7)
  assert.deepEqual(context.consultantWorkloads, [{ consultant_id: 4 }])
  assert.equal(context.consultantWorkloadLoading, false)
})

test('failed consultant workload refresh preserves existing data and exposes a retryable error', async () => {
  const originalGet = apiClient.get
  apiClient.get = async () => { throw new Error('network unavailable') }
  const existingWorkload = [{ consultant_id: 4 }]
  const context = {
    consultantWorkloadLoading: false,
    consultantWorkloadError: '',
    consultantWorkloads: existingWorkload,
    consultantWorkloadPeriodDays: 30,
    errorText: error => error.message
  }

  try {
    await usersMethods.changeConsultantWorkloadPeriod.call(context, 90)
  } finally {
    apiClient.get = originalGet
  }

  assert.equal(context.consultantWorkloadPeriodDays, 30)
  assert.equal(context.consultantWorkloads, existingWorkload)
  assert.equal(context.consultantWorkloadError, 'network unavailable')
  assert.equal(context.consultantWorkloadLoading, false)
})
