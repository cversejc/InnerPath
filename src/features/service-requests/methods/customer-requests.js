import { getMyServiceRequests, withdrawServiceRequest } from '../api.js'
import { submitReportCaseSupplement } from '../../report-cases/api.js'
import { retryCalendarRequest } from '../../calendar/api.js'
import { getMyServiceFeedback } from '../../service-feedback/api.js'
import {
  canWithdrawServiceRequest,
  customerServiceRequestStatusLabel,
  customerServiceTypeLabel,
  formatCustomerServiceRequestDateTime,
  serviceRequestEditPath,
  topicLabel
} from '../customer-formatters.js'

export default {
  async loadFeedback() {
    try {
      const response = await getMyServiceFeedback()
      this.feedbackByRequestId = Object.fromEntries(
        (response.items || [])
          .filter(item => item.service_request_id)
          .map(item => [item.service_request_id, item])
      )
      this.feedbackReady = true
    } catch {
      this.feedbackLoadError = true
    }
  },
  isDeliveredReport(item) {
    return item.service_type === 'report' && item.status === 'delivered' && item.result_type === 'report'
  },
  saveRequestFeedback(requestId, feedback) {
    this.feedbackByRequestId = { ...this.feedbackByRequestId, [requestId]: feedback }
  },
  async loadRequests(silent = false) {
    if (this.requestFetchInFlight) return
    this.requestFetchInFlight = true
    if (!silent) this.loading = true
    try {
      const response = await getMyServiceRequests()
      this.requests = response.items || []
    } catch (error) {
      if (!silent) {
        this.message = this.errorText(error)
        this.messageType = 'error'
      }
    } finally {
      this.requestFetchInFlight = false
      if (!silent) this.loading = false
      this.syncRequestPolling()
    }
  },
  syncRequestPolling() {
    const active = this.requests.some(item =>
      item.workflow_type === 'calendar_generation'
        ? item.status === 'ai_processing'
        : item.workflow_type !== 'calendar_legacy' && ['submitted', 'accepted', 'ai_processing', 'ai_ready', 'reviewing'].includes(item.status)
    )
    if (active && !this.requestRefreshTimer) {
      this.requestRefreshTimer = window.setInterval(() => this.loadRequests(true), 5000)
    } else if (!active && this.requestRefreshTimer) {
      window.clearInterval(this.requestRefreshTimer)
      this.requestRefreshTimer = null
    }
  },
  payload(item) {
    return item.request_payload || {}
  },
  serviceTypeLabel(item) {
    return item.workflow_type === 'calendar_generation'
      ? '日历生成'
      : item.workflow_type === 'calendar_legacy'
        ? '历史日历申请'
      : customerServiceTypeLabel(item.service_type)
  },
  statusLabel(item) {
    if (item.workflow_type === 'calendar_generation') {
      if (item.status === 'ai_processing') return '日历生成中'
      if (item.status === 'delivered') return '已开放使用'
      if (item.status === 'failed') return '生成失败'
    }
    if (item.workflow_type === 'calendar_legacy' && ['submitted', 'accepted', 'ai_processing', 'ai_ready', 'reviewing', 'pending'].includes(item.status)) return '旧流程已停用'
    return customerServiceRequestStatusLabel(item.status)
  },
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
      const index = this.requests.findIndex(request => request.id === item.id && request.service_type === item.service_type && request.workflow_type === item.workflow_type)
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
  async retryCalendar(item) {
    if (this.retryingCalendarId || item.workflow_type !== 'calendar_generation' || item.status !== 'failed') return
    this.retryingCalendarId = item.id
    try {
      await retryCalendarRequest(item.id)
      this.message = '已重新启动日历生成，成功后会自动开放。'
      this.messageType = 'info'
      await this.loadRequests()
    } catch (error) {
      this.message = error.response?.data?.detail || this.errorText(error)
      this.messageType = 'error'
    } finally {
      this.retryingCalendarId = null
    }
  },
  errorText(error) {
    return error.response?.data?.detail || '申请记录加载失败，请稍后重试'
  }
}
