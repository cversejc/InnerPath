import { getAdminCalendarRequests } from '../../calendar/api.js'
import { getAdminServiceRequests } from '../../service-requests/api.js'

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
  }
}
