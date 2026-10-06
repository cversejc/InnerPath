import { logout as logoutUser } from '../../../stores/auth'

export default {
  syncDrawerBodyLock() {
      const hasOpenDrawer = Boolean(this.detailUser || this.reportDetail || this.logDetail)
      document.body.classList.toggle('dialog-open', hasOpenDrawer)
    },
  async switchTab(tab) {
      this.activeTab = tab
      this.mobileNavOpen = false
      if (tab === 'overview') await this.loadDashboard()
      if (tab === 'users') await this.loadUsers()
      if (tab === 'requests') await this.loadAdminRequests()
      if (tab === 'calendar' && !this.calendarUsers.length) await this.loadCalendarUsers()
      if (tab === 'reports') await this.loadReports()
      if (tab === 'logs') await this.loadAuditLogs()
      this.syncAutoRefresh()
    },
  toggleMobileNav() {
      this.mobileNavOpen = !this.mobileNavOpen
    },
  closeMobileNav() {
      this.mobileNavOpen = false
    },
  async refreshActive() {
      if (this.activeTab === 'overview') return this.loadDashboard()
      if (this.activeTab === 'users') return this.loadUsers()
      if (this.activeTab === 'requests') return this.loadAdminRequests()
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
  goFromAlert(alert) {
      const target = alert.route === 'calendar' ? 'calendar' : alert.route === 'reports' ? 'reports' : 'logs'
      this.switchTab(target)
    },
  getDrawer(name) { return this.$refs.adminDetailDrawers?.getDrawer(name) },
  getOpenDrawer() { if (this.logDetail) return this.getDrawer('logDrawer'); if (this.reportDetail) return this.getDrawer('reportDrawer'); if (this.detailUser) return this.getDrawer('userDrawer'); return null },
  focusDrawer(name) { this.$nextTick(() => { const drawer = this.getDrawer(name); if (!drawer) return; const target = drawer.querySelector('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'); (target || drawer).focus({ preventScroll: true }) }) },
  restoreDrawerFocus() { const trigger = this.drawerTrigger; this.drawerTrigger = null; this.$nextTick(() => trigger?.focus?.()) },
  closeActiveDrawer() { if (this.logDetail) return this.closeLogDetail(); if (this.reportDetail) return this.closeReportDetail(); if (this.detailUser) return this.closeUserDetail() },
  cleanParams(params) { return Object.fromEntries(Object.entries(params).filter(([, value]) => value !== '' && value !== null && value !== undefined)) },
  errorText(error) { return error.response?.data?.detail || error.message || '请求失败，请稍后重试' }
}
