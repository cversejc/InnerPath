import {
  clearAccessToken,
  setAccessToken
} from '../../utils/apiClient.js'
import {
  acceptStaffInviteRequest,
  changePhoneRequest,
  deactivateAccountRequest,
  loginRequest,
  logoutRequest,
  registerRequest,
  requestPhoneChangeCodeRequest,
  resetPasswordRequest,
  sendVerificationCodeRequest
} from './api.js'

function saveSession(data) {
  setAccessToken(data.access_token)
  if (data.user) {
    sessionStorage.setItem('user', JSON.stringify(data.user))
  }
  return data
}

export async function sendVerificationCode(phone, purpose) {
  return sendVerificationCodeRequest(phone, purpose)
}

export async function register(phone, password, name, code) {
  return saveSession(await registerRequest(phone, password, name, code))
}

export async function resetPassword(phone, code, newPassword) {
  return resetPasswordRequest(phone, code, newPassword)
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

export async function requestPhoneChangeCode(newPhone) {
  return requestPhoneChangeCodeRequest(newPhone)
}

export async function changePhone(newPhone, code, currentPassword) {
  return changePhoneRequest(newPhone, code, currentPassword)
}

export async function deactivateAccount(currentPassword) {
  return deactivateAccountRequest(currentPassword)
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
