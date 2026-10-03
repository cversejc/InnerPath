import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',  // 允许外部访问
    allowedHosts: ['host.docker.internal'],
    port: 3000,
    open: true,
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true
      }
    }
  },
  // 生产构建预览同样开放局域网访问，并带上后端代理，
  // 手机连同一个 Wi-Fi 时可以直接登录、查看报告与日历
  preview: {
    host: '0.0.0.0',
    port: 4176,
    strictPort: true,
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true
      }
    }
  }
})
