import apiClient, {
  clearAccessToken,
  refreshAccessToken,
  setAccessToken
} from './apiClient'

function saveSession(data) {
  setAccessToken(data.access_token)
  if (data.user) {
    sessionStorage.setItem('user', JSON.stringify(data.user))
  }
  return data
}

export async function register(phone, password, name) {
  const response = await apiClient.post('/auth/register', { phone, password, name })
  return saveSession(response.data)
}

export async function login(phone, password) {
  const response = await apiClient.post('/auth/login', { phone, password })
  return saveSession(response.data)
}

export async function acceptStaffInvite(token, phone, password, name) {
  const response = await apiClient.post('/auth/staff/accept-invite', {
    token,
    phone,
    password,
    name
  })
  return saveSession(response.data)
}

export async function logout() {
  try {
    await apiClient.post('/auth/logout')
  } finally {
    clearAccessToken()
    sessionStorage.removeItem('user')
  }
}

export async function getCurrentUser() {
  const response = await apiClient.get('/users/me')
  sessionStorage.setItem('user', JSON.stringify(response.data))
  return response.data
}

export async function updateUserProfile(userData) {
  const response = await apiClient.put('/users/me', userData)
  sessionStorage.setItem('user', JSON.stringify(response.data))
  return response.data
}

export async function changePassword(currentPassword, newPassword) {
  const response = await apiClient.post('/users/me/change-password', {
    current_password: currentPassword,
    new_password: newPassword
  })
  return response.data
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

export { refreshAccessToken }

export default {
  register,
  login,
  acceptStaffInvite,
  logout,
  getCurrentUser,
  updateUserProfile,
  changePassword,
  isAuthenticated,
  getStoredUser,
  refreshAccessToken
}
