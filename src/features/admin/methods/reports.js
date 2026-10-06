import {
  getAdminReport,
  getAdminReportTasks,
  getAdminReports
} from '../../reports/api.js'

export default {
  async setReportSection(section) {
      this.reportSection = section
      if (section === 'reports') await this.loadReports()
      else await this.loadReportTasks()
    },
  async loadReports() {
      const requestId = this.reportListRequestId + 1
      this.reportListRequestId = requestId
      this.reportsLoading = true
      try {
        const reports = await getAdminReports({ ...this.cleanParams(this.reportFilters), page: this.reportPage, size: this.reportPageSize })
        if (this.reportListRequestId === requestId) this.reports = reports
      } catch (error) {
        if (this.reportListRequestId === requestId) this.message = this.errorText(error)
      } finally {
        if (this.reportListRequestId === requestId) this.reportsLoading = false
      }
    },
  async searchReports() { this.reportPage = 1; await this.loadReports() },
  async changeReportPage(offset) { const next = this.reportPage + offset; if (next < 1 || next > this.pageCount(this.reports.total, this.reportPageSize)) return; this.reportPage = next; await this.loadReports() },
  async loadReportTasks() {
      const requestId = this.reportTaskRequestId + 1
      this.reportTaskRequestId = requestId
      this.tasksLoading = true
      try {
        const tasks = await getAdminReportTasks({ ...this.cleanParams(this.taskFilters), page: this.taskPage, size: this.taskPageSize })
        if (this.reportTaskRequestId === requestId) this.reportTasks = tasks
      } catch (error) {
        if (this.reportTaskRequestId === requestId) this.message = this.errorText(error)
      } finally {
        if (this.reportTaskRequestId === requestId) this.tasksLoading = false
      }
    },
  async searchReportTasks() { this.taskPage = 1; await this.loadReportTasks() },
  async changeTaskPage(offset) { const next = this.taskPage + offset; if (next < 1 || next > this.pageCount(this.reportTasks.total, this.taskPageSize)) return; this.taskPage = next; await this.loadReportTasks() },
  async openReport(report) {
      const requestId = this.reportDetailRequestId + 1
      this.reportDetailRequestId = requestId
      this.drawerTrigger = document.activeElement
      this.reportDetail = null
      try {
        const detail = await getAdminReport(report.id)
        if (this.reportDetailRequestId !== requestId) return
        this.reportDetail = detail
        this.focusDrawer('reportDrawer')
      } catch (error) {
        if (this.reportDetailRequestId === requestId) {
          this.message = this.errorText(error)
          this.drawerTrigger = null
        }
      }
    },
  closeReportDetail() {
      this.reportDetailRequestId += 1
      this.reportDetail = null
      this.restoreDrawerFocus()
    }
}
