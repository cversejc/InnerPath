import { logout as logoutUser } from '../../../stores/auth.js'

export default {
  syncDrawerBodyLock() {
      const hasOpenDrawer = Boolean(this.detailUser || this.reportDetail || this.logDetail)
      document.body.classList.toggle('dialog-open', hasOpenDrawer)
    },
  async switchTab(tab) {
      this.activeTab = tab
      if (tab === 'overview') await this.loadDashboard()
      if (tab === 'users') await this.loadUsers()
      if (tab === 'requests') await this.loadAdminRequests()
      if (tab === 'feedback') {
        if (this.feedbackView === 'quality') await this.loadQualityIssues()
        else await this.loadServiceFeedback()
      }
      if (tab === 'calendar' && !this.calendarUsers.length) await this.loadCalendarUsers()
      if (tab === 'reports') {
        if (this.reportSection === 'tasks') await this.loadReportTasks()
        else await this.loadReports()
      }
      if (tab === 'logs') await this.loadAuditLogs()
      this.syncAutoRefresh()
    },
  async refreshActive() {
      if (this.activeTab === 'overview') return this.loadDashboard()
      if (this.activeTab === 'users') return this.loadUsers()
      if (this.activeTab === 'requests') return this.loadAdminRequests()
      if (this.activeTab === 'feedback') return this.feedbackView === 'quality' ? this.loadQualityIssues() : this.loadServiceFeedback()
      if (this.activeTab === 'calendar') return this.selectedCalendarUser ? this.loadCalendars() : this.loadCalendarUsers()
      if (this.activeTab === 'reports') return this.reportSection === 'reports' ? this.loadReports() : this.loadReportTasks()
       if (this.activeTab === 'logs') return this.logSection === 'audit' ? this.loadAuditLogs() : this.logSection === 'behavior' ? this.loadDecisionLogs() : this.loadReportTasks()
      return this.loadStaff()
    },
  async handleLogout() {
      if (this.loggingOut) return
      this.loggingOut = true
      try {
        await logoutUser()
      } catch {
        // 本地会话由 logoutUser 在 finally 中清理，退出接口异常时仍返回登录页。
      } finally {
        await this.$router.replace('/auth/login')
      }
    },
  syncAutoRefresh() {
      this.clearRefreshTimer()
      if (this.autoRefresh && this.activeTab === 'overview' && document.visibilityState === 'visible') {
        this.refreshTimer = window.setInterval(() => this.loadDashboard(true), 60000)
      }
    },
  clearRefreshTimer() {
      if (this.refreshTimer) window.clearInterval(this.refreshTimer)
      this.refreshTimer = null
    },
  handleVisibilityChange() {
      this.syncAutoRefresh()
    },
  async goFromAlert(alert) {
      const serviceQueueFilters = {
        incomplete_assignment: 'incomplete_assignment',
        incomplete_assignment_over_24h: 'incomplete_assignment_over_24h',
        stale_service_requests: 'stale_over_24h',
        workflow_attention: 'workflow_attention'
      }
      if (serviceQueueFilters[alert.key] || ['failed_service_requests'].includes(alert.key)) {
        this.requestKind = 'consultant'
        this.requestFilters = {
          search: '',
          status: alert.key === 'failed_service_requests' ? 'failed' : '',
          consultant_id: '',
          queue_filter: serviceQueueFilters[alert.key] || '',
          date_from: '',
          date_to: ''
        }
        this.requestPage = 1
        await this.switchTab('requests')
        return
      }
      if (['failed_calendar_requests', 'stalled_calendar_requests'].includes(alert.key)) {
        this.requestKind = 'calendar'
        this.calendarRequestFilters = {
          search: '',
          status: alert.key === 'failed_calendar_requests' ? 'failed' : '',
          stalled_only: alert.key === 'stalled_calendar_requests',
          date_from: '',
          date_to: ''
        }
        this.requestPage = 1
        await this.switchTab('requests')
        return
      }
      if (alert.key === 'failed_reports') {
        this.reportSection = 'tasks'
        this.taskFilters = { search: '', status: 'failed' }
        this.taskPage = 1
        await this.switchTab('reports')
        return
      }
      const target = alert.route === 'calendar' ? 'calendar' : alert.route === 'reports' ? 'reports' : 'logs'
      await this.switchTab(target)
    },
  openReportWorkflow(item) {
      return this.$router.push({
        path: '/staff',
        query: {
          scope: 'all',
          request_id: String(item.id),
          section: 'overview'
        }
      })
    },
  getDrawer(name) { return this.$refs.adminDetailDrawers?.getDrawer(name) },
  getOpenDrawer() { if (this.logDetail) return this.getDrawer('logDrawer'); if (this.reportDetail) return this.getDrawer('reportDrawer'); if (this.detailUser) return this.getDrawer('userDrawer'); return null },
  focusDrawer(name) { this.$nextTick(() => { const drawer = this.getDrawer(name); if (!drawer) return; const target = drawer.querySelector('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'); (target || drawer).focus({ preventScroll: true }) }) },
  restoreDrawerFocus() { const trigger = this.drawerTrigger; this.drawerTrigger = null; this.$nextTick(() => trigger?.focus?.()) },
  closeActiveDrawer() { if (this.logDetail) return this.closeLogDetail(); if (this.reportDetail) return this.closeReportDetail(); if (this.detailUser) return this.closeUserDetail() },
  cleanParams(params) { return Object.fromEntries(Object.entries(params).filter(([, value]) => value !== '' && value !== null && value !== undefined)) },
  errorText(error) { return error.response?.data?.detail || error.message || '请求失败，请稍后重试' }
}
