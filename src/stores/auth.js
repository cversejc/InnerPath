import { reactive } from 'vue'
import {
  clearAccessToken,
  getAccessToken,
  refreshAccessToken
} from '../utils/apiClient'
import {
  getCurrentUser,
  getStoredUser,
  logout as logoutRequest
} from '../utils/authService'

export const authState = reactive({
  user: getStoredUser(),
  initialized: false,
  loading: false
})

let initializationPromise = null

export async function initializeAuth() {
  if (authState.initialized && (authState.user || getAccessToken())) {
    if (getAccessToken()) return authState.user
    authState.initialized = false
  }
  if (initializationPromise) return initializationPromise

  authState.loading = true
  initializationPromise = (async () => {
    try {
      if (!getAccessToken()) {
        await refreshAccessToken()
      }
      authState.user = await getCurrentUser()
      return authState.user
    } catch (error) {
      clearAuthState()
      return null
    } finally {
      authState.initialized = true
      authState.loading = false
      initializationPromise = null
    }
  })()

  return initializationPromise
}

export function setAuthenticatedUser(user) {
  authState.user = user
  authState.initialized = true
}

export function clearAuthState() {
  authState.user = null
  clearAccessToken()
  sessionStorage.removeItem('user')
}

export function hasRole(...roles) {
  return Boolean(authState.user && roles.includes(authState.user.role))
}

export async function logout() {
  try {
    await logoutRequest()
  } finally {
    clearAuthState()
  }
}
