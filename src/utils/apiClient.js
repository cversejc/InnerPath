import axios from 'axios'
import apiConfig from './apiConfig'

const ACCESS_TOKEN_KEY = 'access_token'

const rawClient = axios.create({
  baseURL: apiConfig.baseURL,
  timeout: apiConfig.timeout,
  withCredentials: true
})

const apiClient = axios.create({
  baseURL: apiConfig.baseURL,
  timeout: apiConfig.timeout,
  withCredentials: true
})

let refreshPromise = null

export function getAccessToken() {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY)
}

export function setAccessToken(token) {
  if (token) {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, token)
  } else {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY)
  }
}

export function clearAccessToken() {
  setAccessToken(null)
}

export async function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = rawClient.post('/auth/refresh').then(response => {
      setAccessToken(response.data.access_token)
      return response.data.access_token
    }).finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

apiClient.interceptors.request.use(config => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  response => response,
  async error => {
    const config = error.config
    const isAuthRequest = config?.url?.includes('/auth/')
    if (error.response?.status === 401 && config && !config._retry && !isAuthRequest) {
      config._retry = true
      try {
        const token = await refreshAccessToken()
        config.headers.Authorization = `Bearer ${token}`
        return apiClient(config)
      } catch (refreshError) {
        clearAccessToken()
        sessionStorage.removeItem('user')
        return Promise.reject(refreshError)
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient
