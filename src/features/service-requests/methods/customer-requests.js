import { getMyServiceRequests, withdrawServiceRequest } from '../api.js'
import { submitReportCaseSupplement } from '../../report-cases/api.js'
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
    const confirmed = await this.confirmAction({
      title: '确认撤回申请',
      message: '确定撤回这份申请吗？撤回后需要重新提交才能继续。',
      confirmButtonText: '确认撤回'
    })
    if (!confirmed) return
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
  async submitReportSupplement(item) {
    const answer = String(this.followUpAnswers[item.id] || '').trim()
    if (item.service_type !== 'report' || !item.report_case_id || !answer || this.supplementSubmittingId) return

    let pendingKey = this.followUpResponseKeys[item.id]
    if (!pendingKey || pendingKey.answer !== answer) {
      pendingKey = {
        answer,
        key: `report-follow-up-${item.id}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
      }
      this.followUpResponseKeys = { ...this.followUpResponseKeys, [item.id]: pendingKey }
    }

    this.supplementSubmittingId = item.id
    try {
      await submitReportCaseSupplement(item.report_case_id, {
        response_key: pendingKey.key,
        answer
      })
      this.followUpAnswers = { ...this.followUpAnswers, [item.id]: '' }
      const { [item.id]: _submitted, ...remainingKeys } = this.followUpResponseKeys
      this.followUpResponseKeys = remainingKeys
      this.message = '补充资料已提交，咨询师会继续审核当前节点。'
      this.messageType = 'info'
      await this.loadRequests()
    } catch (error) {
      this.message = this.errorText(error)
      this.messageType = 'error'
    } finally {
      this.supplementSubmittingId = null
    }
  },
  errorText(error) {
    return error.response?.data?.detail || '申请记录加载失败，请稍后重试'
  }
}
