import assert from 'node:assert/strict'
import test from 'node:test'
import apiClient from '../../utils/apiClient.js'
import { getCurrentUser, updateUserProfile } from './service.js'

test('current user requests update the cached session user', async () => {
  const originalGet = apiClient.get
  const originalPut = apiClient.put
  const originalSessionStorage = globalThis.sessionStorage
  const cachedValues = new Map()
  const requests = []
  const user = { id: 7, name: '林一' }

  globalThis.sessionStorage = {
    setItem(key, value) {
      cachedValues.set(key, value)
    }
  }
  apiClient.get = async url => {
    requests.push(['get', url])
    return { data: user }
  }
  apiClient.put = async (url, data) => {
    requests.push(['put', url, data])
    return { data: user }
  }

  try {
    assert.deepEqual(await getCurrentUser(), user)
    assert.deepEqual(await updateUserProfile({ name: '林一' }), user)
    assert.deepEqual(requests, [
      ['get', '/users/me'],
      ['put', '/users/me', { name: '林一' }]
    ])
    assert.equal(cachedValues.get('user'), JSON.stringify(user))
  } finally {
    apiClient.get = originalGet
    apiClient.put = originalPut
    if (originalSessionStorage === undefined) {
      delete globalThis.sessionStorage
    } else {
      globalThis.sessionStorage = originalSessionStorage
    }
  }
})
