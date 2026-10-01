import assert from 'node:assert/strict'
import test from 'node:test'
import apiClient from '../../utils/apiClient.js'
import { getStoredUser, isAuthenticated, login, logout } from './session.js'

function mockSessionStorage(initialValues = {}) {
  const values = new Map(Object.entries(initialValues))
  return {
    values,
    getItem(key) {
      return values.get(key) ?? null
    },
    setItem(key, value) {
      values.set(key, String(value))
    },
    removeItem(key) {
      values.delete(key)
    }
  }
}

test('login saves the access token and cached user', async () => {
  const originalPost = apiClient.post
  const originalSessionStorage = globalThis.sessionStorage
  const storage = mockSessionStorage()
  const user = { id: 7, role: 'user' }
  globalThis.sessionStorage = storage
  apiClient.post = async () => ({ data: { access_token: 'token-123', user } })

  try {
    assert.deepEqual(await login('13800000000', 'secret'), { access_token: 'token-123', user })
    assert.equal(storage.getItem('access_token'), 'token-123')
    assert.deepEqual(getStoredUser(), user)
    assert.equal(isAuthenticated(), true)
  } finally {
    apiClient.post = originalPost
    if (originalSessionStorage === undefined) {
      delete globalThis.sessionStorage
    } else {
      globalThis.sessionStorage = originalSessionStorage
    }
  }
})

test('logout clears the local session even when its request fails', async () => {
  const originalPost = apiClient.post
  const originalSessionStorage = globalThis.sessionStorage
  const storage = mockSessionStorage({
    access_token: 'token-123',
    user: JSON.stringify({ id: 7 })
  })
  globalThis.sessionStorage = storage
  apiClient.post = async () => {
    throw new Error('network unavailable')
  }

  try {
    await assert.rejects(logout(), /network unavailable/)
    assert.equal(storage.getItem('access_token'), null)
    assert.equal(storage.getItem('user'), null)
  } finally {
    apiClient.post = originalPost
    if (originalSessionStorage === undefined) {
      delete globalThis.sessionStorage
    } else {
      globalThis.sessionStorage = originalSessionStorage
    }
  }
})

test('invalid cached users are removed', () => {
  const originalSessionStorage = globalThis.sessionStorage
  const storage = mockSessionStorage({ user: '{invalid' })
  globalThis.sessionStorage = storage

  try {
    assert.equal(getStoredUser(), null)
    assert.equal(storage.getItem('user'), null)
  } finally {
    if (originalSessionStorage === undefined) {
      delete globalThis.sessionStorage
    } else {
      globalThis.sessionStorage = originalSessionStorage
    }
  }
})
