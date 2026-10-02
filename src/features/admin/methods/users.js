import {
  getAdminAuditLogs,
  getAdminUser,
  getAdminUserSummary,
  getAdminUsers,
  getAllAdminUsers,
  resetAdminUserPassword,
  updateAdminUserProfile,
  updateAdminUserRole,
  updateAdminUserStatus
} from '../api.js'
import { getAdminCalendars, getAdminUserDecisionLogs } from '../../calendar/api.js'
import { getAdminReports } from '../../reports/api.js'

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
      try { const [admins, consultants] = await Promise.all([getAllAdminUsers({ role: 'admin', size: 100 }), getAllAdminUsers({ role: 'consultant', size: 100 })]); this.staffUsers = [...(admins.items || []), ...(consultants.items || [])].sort((a, b) => a.id - b.id) } catch (error) { this.message = this.errorText(error) } finally { this.staffLoading = false }
    },
  async openUserDetail(user) {
      this.drawerTrigger = document.activeElement
      this.detailUser = user
      this.userPanelTab = 'profile'
      this.userPanelLoading = true
      this.focusDrawer('userDrawer')
      try {
        const [detail, summary] = await Promise.all([getAdminUser(user.id), getAdminUserSummary(user.id)])
        this.detailUser = detail
        this.userSummary = summary
        this.userEdit = this.toUserEdit(detail)
      this.userPanelData = { reports: null, calendars: null, decisions: null, activity: null }
      } catch (error) { this.message = this.errorText(error); this.detailUser = null } finally { this.userPanelLoading = false }
    },
  closeUserDetail({ restoreFocus = true } = {}) { this.detailUser = null; this.userSummary = null; if (restoreFocus) this.restoreDrawerFocus() },
  async setUserPanelTab(tab) {
      this.userPanelTab = tab
      if (!this.detailUser || tab === 'profile') return
      this.userPanelLoading = true
      try {
        const id = this.detailUser.id
        if (tab === 'reports') this.userPanelData.reports = await getAdminReports({ user_id: id, page: 1, size: 100 })
        if (tab === 'calendar') this.userPanelData.calendars = (await getAdminCalendars(id)).items || []
        if (tab === 'decisions') this.userPanelData.decisions = await getAdminUserDecisionLogs(id, { page: 1, size: 100 })
        if (tab === 'activity') this.userPanelData.activity = await getAdminAuditLogs({ target_user_id: id, page: 1, size: 100 })
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
