// 开发环境优先使用 Vite 的同源代理，这样电脑和局域网手机都能访问同一个 API 地址。
const configuredBaseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
const browserHostname = typeof window === 'undefined' ? '' : window.location.hostname
const isRemoteBrowser = browserHostname && !['localhost', '127.0.0.1', '::1'].includes(browserHostname)
const pointsToLoopback = /^https?:\/\/(localhost|127\.0\.0\.1|\[::1\])(?::\d+)?\//i.test(configuredBaseURL)
const API_BASE_URL = isRemoteBrowser && pointsToLoopback ? '/api/v1' : configuredBaseURL

export default {
  baseURL: API_BASE_URL,
  timeout: 120000  // 120秒超时（多步AI生成需要更长时间）
}
