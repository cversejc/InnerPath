// API配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export default {
  baseURL: API_BASE_URL,
  timeout: 120000  // 120秒超时（多步AI生成需要更长时间）
}
