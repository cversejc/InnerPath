import assert from 'node:assert/strict'
import test from 'node:test'
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
