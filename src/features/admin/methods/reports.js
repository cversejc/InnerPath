import {
  getAdminReport,
  getAdminReportTasks,
  getAdminReports,
  retryAdminReportTask
} from '../../reports/api.js'

export default {
  async setReportSection(section) {
      this.reportSection = section
      if (section === 'reports') await this.loadReports()
      else await this.loadReportTasks()
    },
  async loadReports() { this.reportsLoading = true; try { this.reports = await getAdminReports({ ...this.cleanParams(this.reportFilters), page: this.reportPage, size: this.reportPageSize }) } catch (error) { this.message = this.errorText(error) } finally { this.reportsLoading = false } },
  async searchReports() { this.reportPage = 1; await this.loadReports() },
  async changeReportPage(offset) { const next = this.reportPage + offset; if (next < 1 || next > this.pageCount(this.reports.total, this.reportPageSize)) return; this.reportPage = next; await this.loadReports() },
  async loadReportTasks() { this.tasksLoading = true; try { this.reportTasks = await getAdminReportTasks({ ...this.cleanParams(this.taskFilters), page: this.taskPage, size: this.taskPageSize }) } catch (error) { this.message = this.errorText(error) } finally { this.tasksLoading = false } },
  async searchReportTasks() { this.taskPage = 1; await this.loadReportTasks() },
  async changeTaskPage(offset) { const next = this.taskPage + offset; if (next < 1 || next > this.pageCount(this.reportTasks.total, this.taskPageSize)) return; this.taskPage = next; await this.loadReportTasks() },
  canRetryTask(task) { return task.status === 'failed' && task.has_input_snapshot && !task.has_retry && task.retry_count < this.reportRetryLimit },
  async retryTask(task) {
      const confirmed = await this.confirmAction({
        title: '确认重新生成报告',
        message: '确认重新生成这份报告？这会再次调用 AI 服务。',
        confirmButtonText: '确认重试'
      })
      if (!confirmed) return
      try {
        await retryAdminReportTask(task.task_id)
        this.message = '重试任务已排队'
        await this.loadReportTasks()
      } catch (error) {
        this.message = this.errorText(error)
      }
    },
  async openReport(report) { this.drawerTrigger = document.activeElement; try { this.reportDetail = await getAdminReport(report.id); this.focusDrawer('reportDrawer') } catch (error) { this.message = this.errorText(error); this.drawerTrigger = null } },
  closeReportDetail() { this.reportDetail = null; this.restoreDrawerFocus() }
}
