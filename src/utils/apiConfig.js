// API配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export default {
  baseURL: API_BASE_URL,
  timeout: 60000  // 60秒超时（AI生成需要时间）
}
