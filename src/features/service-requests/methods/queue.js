import {
  acceptStaffServiceRequest,
  getStaffServiceRequestWorkspace,
  getStaffServiceRequests
} from '../api.js'
import { calendarEditorFromPayload, reportEditorFromPayload } from '../payloads.js'

export default {
  async loadRequests() {
    this.loading = true
    try {
      this.requests = await getStaffServiceRequests({
        scope: this.scope,
        service_type: this.serviceType || undefined,
        status: this.statusFilter || undefined
      })
      if (this.selectedRequest) {
        const refreshed = this.requests.items.find(item => item.id === this.selectedRequest.id)
        if (refreshed) {
          this.selectedRequest = refreshed
        } else {
          this.selectedRequest = null
          this.workspace = null
          this.reportCase = null
          this.reportCaseCompletionGate = null
          this.reportCaseContent = { evidence: [], findings: [], fragments: [] }
          this.stopPolling()
        }
      }
      if (!this.selectedRequest && !this.admin && this.scope === 'mine') {
        const reportRequests = this.requests.items
          .filter(item => item.service_type === 'report' && item.current_step_key)
          .sort((left, right) => {
            const leftStep = Number(String(left.current_step_key).replace('S', '')) || Infinity
            const rightStep = Number(String(right.current_step_key).replace('S', '')) || Infinity
            return leftStep - rightStep || left.id - right.id
          })
        const nextRequest = reportRequests[0]
        if (nextRequest) await this.selectRequest(nextRequest)
      }
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.loading = false
    }
  },
  async changeScope(scope) {
    this.scope = scope
    this.selectedRequest = null
    this.workspace = null
    this.reportCase = null
    this.reportCaseCompletionGate = null
    this.reportCaseContent = { evidence: [], findings: [], fragments: [] }
    this.stopPolling()
    await this.loadRequests()
  },
  async selectRequest(item) {
    this.stopPolling()
    this.selectedRequest = item
    this.workspace = null
    this.reportCase = null
    this.reportCaseCompletionGate = null
    this.reportCaseContent = { evidence: [], findings: [], fragments: [] }
    this.reportAnalysisRuns = []
    this.message = ''
    if (item.assigned_consultant_id || this.admin) await this.loadWorkspace(item.id)
  },
  async loadWorkspace(requestId) {
    this.loading = true
    try {
      this.workspace = await getStaffServiceRequestWorkspace(requestId)
      this.assignmentId = this.workspace.request.assigned_consultant_id ?? null
      if (this.workspace.draft) {
        if (this.workspace.request.service_type === 'report') {
          this.reportEditor = reportEditorFromPayload(this.workspace.draft.editable_payload)
        } else {
          this.calendarEditor = calendarEditorFromPayload(this.workspace.draft.editable_payload)
        }
      }
      if (this.workspace.request.service_type === 'report' && this.workspace.request.report_case_id) {
        await this.loadReportCaseData(this.workspace.request.report_case_id)
      } else {
        this.reportCase = null
        this.reportCaseContent = { evidence: [], findings: [], fragments: [] }
      }
      if (this.workspace.task?.status === 'processing') this.startPolling(this.workspace.task)
    } catch (error) {
      this.workspace = null
      this.message = this.errorText(error)
    } finally {
      this.loading = false
    }
  },
  async acceptRequest() {
    if (!this.selectedRequest || this.accepting) return
    this.accepting = true
    try {
      await acceptStaffServiceRequest(this.selectedRequest.id)
      this.message = '申请已接收，完整资料已开放。'
      await this.loadRequests()
      await this.loadWorkspace(this.selectedRequest.id)
    } catch (error) {
      this.message = this.errorText(error)
      await this.loadRequests()
    } finally {
      this.accepting = false
    }
  }
}
