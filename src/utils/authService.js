import axios from 'axios'
import apiConfig from './apiConfig'

// 创建axios实例
const apiClient = axios.create({
  baseURL: apiConfig.baseURL,
  timeout: apiConfig.timeout
})

// 请求拦截器 - 自动添加token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 处理401错误
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Token过期或无效，清除并跳转到登录
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      // 可以在这里跳转到登录页面
      // window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

/**
 * 发送验证码
 */
export async function sendVerificationCode(phone) {
  const response = await apiClient.post('/auth/send-code', { phone })
  return response.data
}

/**
 * 登录/注册
 */
export async function login(phone, code) {
  const response = await apiClient.post('/auth/login', { phone, code })
  const { access_token, user } = response.data

  // 保存token和用户信息
  localStorage.setItem('access_token', access_token)
  localStorage.setItem('user', JSON.stringify(user))

  return response.data
}

/**
 * 登出
 */
export async function logout() {
  await apiClient.post('/auth/logout')
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
}

/**
 * 获取当前用户信息
 */
export async function getCurrentUser() {
  const response = await apiClient.get('/users/me')
  return response.data
}

/**
 * 更新用户信息
 */
export async function updateUserProfile(userData) {
  const response = await apiClient.put('/users/me', userData)
  return response.data
}

/**
 * 检查是否已登录
 */
export function isAuthenticated() {
  return !!localStorage.getItem('access_token')
}

/**
 * 获取存储的用户信息
 */
export function getStoredUser() {
  const userStr = localStorage.getItem('user')
  return userStr ? JSON.parse(userStr) : null
}

export default {
  sendVerificationCode,
  login,
  logout,
  getCurrentUser,
  updateUserProfile,
  isAuthenticated,
  getStoredUser
}
