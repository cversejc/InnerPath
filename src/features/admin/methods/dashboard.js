import { getAdminDashboard } from '../api'
import { formatDateTime } from '../../../utils/dateTime.js'

export default {
  async loadDashboard(silent = false) {
      if (!silent) this.dashboardLoading = true
      try {
        this.dashboard = await getAdminDashboard(this.dashboardRange)
        this.lastUpdated = formatDateTime(new Date())
      } catch (error) {
        if (!silent) this.message = this.errorText(error)
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
