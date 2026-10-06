import { getAdminDashboard } from '../api'

export default {
  async loadDashboard(silent = false) {
      if (!silent) this.dashboardLoading = true
      this.dashboardLoadError = false
      try {
        this.dashboard = await getAdminDashboard(this.dashboardRange)
        this.lastUpdated = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      } catch {
        this.dashboardLoadError = true
      } finally {
        this.dashboardLoading = false
      }
    },
  async changeDashboardRange(range) {
      if (this.dashboardRange === range) return
      this.dashboardRange = range
      await this.loadDashboard()
    },
  setAutoRefresh(enabled) {
      this.autoRefresh = enabled
      this.syncAutoRefresh()
    }
}
