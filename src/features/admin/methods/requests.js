import { getAdminCalendarRequests } from '../../calendar/api.js'
import { getAdminServiceRequests, updateAdminServiceRequestAssignment } from '../../service-requests/api.js'

export default {
  async loadAdminRequests() {
    this.requestsLoading = true
    try {
      if (this.requestKind === 'calendar') {
        this.adminCalendarRequests = await getAdminCalendarRequests({
          ...this.cleanParams(this.calendarRequestFilters),
          page: this.requestPage,
          size: this.requestPageSize
        })
      } else {
        this.adminServiceRequests = await getAdminServiceRequests({
          ...this.cleanParams(this.requestFilters),
          page: this.requestPage,
          size: this.requestPageSize
        })
      }
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.requestsLoading = false
    }
  },
  async setRequestKind(kind) {
    if (this.requestKind === kind) return
    this.assignmentRequest = null
    this.requestKind = kind
    this.requestPage = 1
    await this.loadAdminRequests()
  },
  async searchAdminRequests() {
    this.requestPage = 1
    await this.loadAdminRequests()
  },
  resetAdminRequestFilters() {
    if (this.requestKind === 'calendar') {
      this.calendarRequestFilters = { search: '', status: '', date_from: '', date_to: '' }
    } else {
      this.requestFilters = { search: '', status: '', consultant_id: '', date_from: '', date_to: '' }
    }
    this.searchAdminRequests()
  },
  async changeRequestPage(offset) {
    const data = this.requestKind === 'calendar' ? this.adminCalendarRequests : this.adminServiceRequests
    const next = this.requestPage + offset
    if (next < 1 || next > this.pageCount(data.total, this.requestPageSize)) return
    this.requestPage = next
    await this.loadAdminRequests()
  },
  async openConsultantServiceRequests(consultantId) {
    this.assignmentRequest = null
    this.requestKind = 'consultant'
    this.requestFilters = {
      search: '',
      status: '',
      consultant_id: String(consultantId),
      date_from: '',
      date_to: ''
    }
    this.requestPage = 1
    this.activeTab = 'requests'
    await this.loadAdminRequests()
  },
  openAdminAssignment(request) {
    this.assignmentRequest = request
    this.assignmentError = ''
  },
  closeAdminAssignment() {
    if (!this.assignmentSavingKey) this.assignmentRequest = null
  },
  async assignAdminRequest(change) {
    if (this.assignmentSavingKey) return
    const key = `${change.requestId}:${change.mode || 'single'}`
    this.assignmentSavingKey = key
    this.assignmentError = ''
    try {
      await updateAdminServiceRequestAssignment(
        change.requestId,
        change.consultantId,
        change.consultantType,
        change.consultationType
      )
      await this.loadAdminRequests()
      if (change.mode === 'mingli' || change.mode === 'psychology') {
        this.assignmentRequest = this.adminServiceRequests.items.find(item => item.id === change.requestId) || null
      } else {
        this.assignmentRequest = null
      }
      if (change.mode === 'mingli') this.message = change.consultantId ? '命理负责人已更新。' : '命理席位已清空。'
      else if (change.mode === 'psychology') this.message = change.consultantId ? '心理负责人已更新。' : '心理席位已清空。'
      else this.message = change.consultantId ? '咨询方向与负责人已保存。' : '咨询方向已保存，申请当前未分配。'
    } catch (error) {
      this.assignmentError = this.errorText(error)
    } finally {
      this.assignmentSavingKey = ''
    }
  }
}
