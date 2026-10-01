import assert from 'node:assert/strict'
import test from 'node:test'
import apiClient from '../../utils/apiClient.js'
import {
  acceptStaffInviteRequest,
  loginRequest,
  logoutRequest,
  registerRequest,
  resetPasswordRequest,
  sendVerificationCodeRequest
} from './api.js'

test('authentication API maps actions to their endpoint payloads', async () => {
  const originalPost = apiClient.post
  const requests = []
  apiClient.post = async (url, data) => {
    requests.push([url, data])
    return { data: { ok: true } }
  }

  try {
    assert.deepEqual(await sendVerificationCodeRequest('13800000000', 'register'), { ok: true })
    assert.deepEqual(await registerRequest('13800000000', 'secret', '林一', '123456'), { ok: true })
    assert.deepEqual(await resetPasswordRequest('13800000000', '654321', 'new-secret'), { ok: true })
    assert.deepEqual(await loginRequest('13800000000', 'secret'), { ok: true })
    assert.deepEqual(await acceptStaffInviteRequest('invite', '13800000000', 'secret', '林一'), { ok: true })
    assert.deepEqual(await logoutRequest(), { ok: true })
    assert.deepEqual(requests, [
      ['/auth/verification-code', { phone: '13800000000', purpose: 'register' }],
      ['/auth/register', { phone: '13800000000', password: 'secret', name: '林一', code: '123456' }],
      ['/auth/password/reset', { phone: '13800000000', code: '654321', new_password: 'new-secret' }],
      ['/auth/login', { phone: '13800000000', password: 'secret' }],
      ['/auth/staff/accept-invite', {
        token: 'invite',
        phone: '13800000000',
        password: 'secret',
        name: '林一'
      }],
      ['/auth/logout', undefined]
    ])
  } finally {
    apiClient.post = originalPost
  }
})
