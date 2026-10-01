import apiClient from '../../utils/apiClient.js'

export async function registerRequest(phone, password, name) {
  const response = await apiClient.post('/auth/register', { phone, password, name })
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
