import {
  clearAccessToken,
  setAccessToken
} from '../../utils/apiClient.js'
import {
  acceptStaffInviteRequest,
  loginRequest,
  logoutRequest,
  registerRequest
} from './api.js'

function saveSession(data) {
  setAccessToken(data.access_token)
  if (data.user) {
    sessionStorage.setItem('user', JSON.stringify(data.user))
  }
  return data
}

export async function register(phone, password, name) {
  return saveSession(await registerRequest(phone, password, name))
}

export async function login(phone, password) {
  return saveSession(await loginRequest(phone, password))
}

export async function acceptStaffInvite(token, phone, password, name) {
  return saveSession(await acceptStaffInviteRequest(token, phone, password, name))
}

export async function logout() {
  try {
    await logoutRequest()
  } finally {
    clearAccessToken()
    sessionStorage.removeItem('user')
  }
}

export function isAuthenticated() {
  return Boolean(sessionStorage.getItem('access_token'))
}

export function getStoredUser() {
  const userString = sessionStorage.getItem('user')
  if (!userString) return null
  try {
    return JSON.parse(userString)
  } catch {
    sessionStorage.removeItem('user')
    return null
  }
}
