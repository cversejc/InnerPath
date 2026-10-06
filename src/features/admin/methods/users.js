import {
  getAdminAuditLogs,
  getAdminUser,
  getAdminUserSummary,
  getAdminUserTimeline,
  getAdminUsers,
  getAllAdminUsers,
  getAdminConsultantWorkload,
  resetAdminUserPassword,
  updateAdminUserProfile,
  updateAdminUserRole,
  updateAdminUserStatus
} from '../api.js'
import { getAdminCalendarRequests, getAdminCalendars, getAdminUserDecisionLogs } from '../../calendar/api.js'
import { getAdminReports } from '../../reports/api.js'
import { getAdminServiceRequests } from '../../service-requests/api.js'

async function getAllPages(fetchPage, params, size = 100) {
  const first = await fetchPage({ ...params, page: 1, size })
  const pageCount = Math.ceil((first.total || 0) / size)
  if (pageCount <= 1) return first
  const remaining = await Promise.all(
    Array.from({ length: pageCount - 1 }, (_, index) => fetchPage({ ...params, page: index + 2, size }))
  )
  return { ...first, items: [first.items || [], ...remaining.map(page => page.items || [])].flat() }
}

export default {
  async loadUsers() {
      this.usersLoading = true
      try {
        this.users = await getAdminUsers({ ...this.cleanParams(this.userFilters), page: this.userPage, size: this.userPageSize })
      } catch (error) { this.message = this.errorText(error) } finally { this.usersLoading = false }
    },
  async searchUsers() { this.userPage = 1; await this.loadUsers() },
  resetUserFilters() { this.userFilters = { search: '', role: '', is_active: '', created_from: '', created_to: '' }; this.searchUsers() },
  async changeUserPage(offset) { const next = this.userPage + offset; if (next < 1 || next > this.pageCount(this.users.total, this.userPageSize)) return; this.userPage = next; await this.loadUsers() },
  async loadStaff() {
      this.staffLoading = true
      this.consultantWorkloadError = ''
      try {
        const [admins, consultants, workload] = await Promise.all([
          getAllAdminUsers({ role: 'admin', size: 100 }),
          getAllAdminUsers({ role: 'consultant', size: 100 }),
          getAdminConsultantWorkload(this.consultantWorkloadPeriodDays).then(data => ({ data })).catch(error => ({ error }))
        ])
        this.staffUsers = [...(admins.items || []), ...(consultants.items || [])].sort((a, b) => a.id - b.id)
        if (workload.error) {
          this.consultantWorkloads = []
          this.consultantWorkloadError = this.errorText(workload.error)
        } else {
          this.consultantWorkloads = workload.data.items || []
          this.consultantWorkloadPeriodDays = workload.data.period_days || 30
        }
      } catch (error) { this.message = this.errorText(error) } finally { this.staffLoading = false }
    },
  async changeConsultantWorkloadPeriod(periodDays) {
      const days = Number(periodDays)
      if (![7, 30, 90].includes(days) || this.consultantWorkloadLoading) return
      this.consultantWorkloadLoading = true
      this.consultantWorkloadError = ''
      try {
        const workload = await getAdminConsultantWorkload(days)
        this.consultantWorkloads = workload.items || []
        this.consultantWorkloadPeriodDays = workload.period_days || days
      } catch (error) {
        this.consultantWorkloadError = this.errorText(error)
      } finally {
        this.consultantWorkloadLoading = false
      }
    },
  async openUserDetail(user) {
      this.drawerTrigger = document.activeElement
      this.detailUser = user
      this.userPanelTab = 'overview'
      this.userPanelLoading = true
      this.timelineLoading = false
      this.timelineError = ''
      this.userPanelData = { timeline: null, reports: null, calendars: null, decisions: null, activity: null, applications: null }
      this.focusDrawer('userDrawer')
      try {
        const [detail, summary] = await Promise.all([getAdminUser(user.id), getAdminUserSummary(user.id)])
        this.detailUser = detail
        this.userSummary = summary
        this.userEdit = this.toUserEdit(detail)
        this.loadUserTimeline()
      } catch (error) { this.message = this.errorText(error); this.detailUser = null } finally { this.userPanelLoading = false }
    },
  closeUserDetail({ restoreFocus = true } = {}) { this.detailUser = null; this.userSummary = null; this.timelineLoading = false; if (restoreFocus) this.restoreDrawerFocus() },
  async loadUserTimeline() {
      if (!this.detailUser || this.timelineLoading) return
      const userId = this.detailUser.id
      this.timelineLoading = true
      this.timelineError = ''
      try {
        const timeline = await getAdminUserTimeline(userId)
        if (this.detailUser?.id === userId) this.userPanelData.timeline = timeline
      } catch (error) {
        if (this.detailUser?.id === userId) this.timelineError = this.errorText(error)
      } finally {
        if (this.detailUser?.id === userId) this.timelineLoading = false
      }
    },
  async setUserPanelTab(tab) {
      this.userPanelTab = tab
      if (!this.detailUser || tab === 'profile') return
      if (tab === 'overview') {
        if (!this.userPanelData.timeline && !this.timelineLoading) await this.loadUserTimeline()
        return
      }
      this.userPanelLoading = true
      try {
        const id = this.detailUser.id
        if (tab === 'applications') {
          const [serviceRequests, calendarRequests] = await Promise.all([
            getAllPages(getAdminServiceRequests, { user_id: id }),
            getAllPages(getAdminCalendarRequests, { user_id: id })
          ])
          this.userPanelData.applications = { serviceRequests, calendarRequests }
        }
        if (tab === 'reports') this.userPanelData.reports = await getAllPages(
          params => getAdminReports(params), { user_id: id }
        )
        if (tab === 'calendar') {
          const [calendars, decisions] = await Promise.all([
            getAdminCalendars(id),
            getAllPages(params => getAdminUserDecisionLogs(id, params), {})
          ])
          this.userPanelData.calendars = calendars.items || []
          this.userPanelData.decisions = decisions
        }
        if (tab === 'decisions') this.userPanelData.decisions = await getAllPages(
          params => getAdminUserDecisionLogs(id, params), {}
        )
        if (tab === 'activity') this.userPanelData.activity = await getAllPages(
          getAdminAuditLogs, { target_user_id: id }
        )
      } catch (error) { this.message = this.errorText(error) } finally { this.userPanelLoading = false }
    },
  toUserEdit(user) {
      return { name: user.name || '', gender: user.gender || '', birth_year: user.birth_year ?? '', birth_month: user.birth_month ?? '', birth_day: user.birth_day ?? '', birth_hour: user.birth_hour ?? '', birth_minute: user.birth_minute ?? '', birth_place: user.birth_place || '', avatar_url: user.avatar_url || '' }
    },
  async saveUserProfile() {
      if (!this.detailUser || this.profileSaving) return
      this.profileSaving = true
      try {
        const payload = { ...this.userEdit }
        payload.gender = payload.gender || null
        ;['birth_year', 'birth_month', 'birth_day', 'birth_hour', 'birth_minute'].forEach(key => { payload[key] = payload[key] === '' ? null : Number(payload[key]) })
        const updated = await updateAdminUserProfile(this.detailUser.id, payload)
        this.detailUser = updated
        this.userEdit = this.toUserEdit(updated)
        this.message = '用户资料已保存'
        await this.loadUsers()
      } catch (error) { this.message = this.errorText(error) } finally { this.profileSaving = false }
    },
  async toggleUser(user) {
      try { const updated = await updateAdminUserStatus(user.id, !user.is_active); Object.assign(user, updated); this.message = '用户状态已更新'; await this.loadStaff() } catch (error) { this.message = this.errorText(error) }
    },
  async changeRole(user, role) {
      try { const updated = await updateAdminUserRole(user.id, role); Object.assign(user, updated); this.message = '用户角色已更新'; await this.loadStaff() } catch (error) { this.message = this.errorText(error); await this.loadUsers() }
    },
  async resetUserPassword(user) {
      if (!user.is_active) { await this.toggleUser(user); return }
      this.passwordDialog = {
        visible: true,
        user,
        password: '',
        showPassword: false,
        error: '',
        submitting: false
      }
    },
  async submitPasswordReset() {
      const { user, password } = this.passwordDialog
      if (!user || this.passwordDialog.submitting) return
      if (password.length < 8) {
        this.passwordDialog.error = '新密码至少需要 8 位'
        return
      }
      this.passwordDialog.submitting = true
      try {
        await resetAdminUserPassword(user.id, password)
        this.message = '密码已重置，原会话已失效'
        this.passwordDialog.visible = false
      } catch (error) {
        this.passwordDialog.error = this.errorText(error)
        this.message = this.passwordDialog.error
      } finally {
        this.passwordDialog.submitting = false
        if (!this.passwordDialog.visible) this.clearPasswordDialog(false)
      }
    },
  clearPasswordDialog(visible) {
      if (visible || this.passwordDialog.submitting) return
      this.passwordDialog.user = null
      this.passwordDialog.password = ''
      this.passwordDialog.showPassword = false
      this.passwordDialog.error = ''
    }
}
