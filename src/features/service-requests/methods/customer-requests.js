import { getMyServiceRequests, withdrawServiceRequest } from '../api.js'
import {
  canWithdrawServiceRequest,
  customerServiceRequestStatusLabel,
  customerServiceTypeLabel,
  formatCustomerServiceRequestDateTime,
  serviceRequestEditPath,
  topicLabel
} from '../customer-formatters.js'

export default {
  async loadRequests() {
    this.loading = true
    try {
      const response = await getMyServiceRequests()
      this.requests = response.items || []
    } catch (error) {
      this.message = this.errorText(error)
      this.messageType = 'error'
    } finally {
      this.loading = false
    }
  },
  payload(item) {
    return item.request_payload || {}
  },
  serviceTypeLabel: customerServiceTypeLabel,
  statusLabel: customerServiceRequestStatusLabel,
  topicLabel,
  formatDateTime: formatCustomerServiceRequestDateTime,
  canWithdraw: canWithdrawServiceRequest,
  editPath: serviceRequestEditPath,
  async withdraw(item) {
    if (!this.canWithdraw(item.status) || this.withdrawnId) return
    if (!window.confirm('确定撤回这份申请吗？撤回后需要重新提交才能继续。')) return
    this.withdrawnId = item.id
    try {
      const updated = await withdrawServiceRequest(item.id)
      const index = this.requests.findIndex(request => request.id === item.id)
      if (index > -1) this.requests.splice(index, 1, updated)
      this.message = '申请已撤回'
      this.messageType = 'info'
    } catch (error) {
      this.message = this.errorText(error)
      this.messageType = 'error'
    } finally {
      this.withdrawnId = null
    }
  },
  errorText(error) {
    return error.response?.data?.detail || '申请记录加载失败，请稍后重试'
  }
}
