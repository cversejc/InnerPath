import apiClient from '../../utils/apiClient.js'

export async function sendVerificationCodeRequest(phone, purpose) {
  const response = await apiClient.post('/auth/verification-code', { phone, purpose })
  return response.data
}

export async function registerRequest(phone, password, name, code) {
  const response = await apiClient.post('/auth/register', { phone, password, name, code })
  return response.data
}

export async function resetPasswordRequest(phone, code, newPassword) {
  const response = await apiClient.post('/auth/password/reset', {
    phone,
    code,
    new_password: newPassword
  })
  return response.data
}

export async function loginRequest(phone, password) {
  const response = await apiClient.post('/auth/login', { phone, password })
  return response.data
}

export async function acceptStaffInviteRequest(token, phone, password, name) {
  const response = await apiClient.post('/auth/staff/accept-invite', {
    token,
    phone,
    password,
    name
  })
  return response.data
}

export async function logoutRequest() {
  const response = await apiClient.post('/auth/logout')
  return response.data
}
