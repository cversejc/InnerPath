import { getAdminDashboard } from '../api.js'
import { formatDateTime } from '../../../utils/dateTime.js'

export default {
  async loadDashboard(silent = false) {
      if (silent && this.dashboardRequestInFlight) return
      const requestId = this.dashboardRequestId + 1
      const range = this.dashboardRange
      this.dashboardRequestId = requestId
      this.dashboardRequestInFlight = true
      if (!silent) this.dashboardLoading = true
      this.dashboardLoadError = false
      try {
        const dashboard = await getAdminDashboard(range)
        if (this.dashboardRequestId !== requestId || this.dashboardRange !== range) return
        this.dashboard = dashboard
        this.lastUpdated = formatDateTime(new Date())
      } catch (error) {
        if (this.dashboardRequestId === requestId && this.dashboardRange === range) this.dashboardLoadError = true
        if (!silent) this.message = this.errorText(error)
      } finally {
        if (this.dashboardRequestId === requestId) {
          this.dashboardRequestInFlight = false
          this.dashboardLoading = false
        }
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
