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
  isAuthenticated,
  getStoredUser,
  refreshAccessToken
}
