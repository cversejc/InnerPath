import {
  acceptStaffServiceRequest,
  getStaffServiceRequestWorkspace,
  getStaffServiceRequests,
  releaseStaffServiceRequest
} from '../api.js'
import { ownsRequest } from '../../report-cases/professional-ownership.js'
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
          this.syncWorkspaceRoute(null)
          this.stopPolling()
        }
      }
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.loading = false
    }
  },
  async changeScope(scope) {
    this.scope = scope
    this.syncWorkspaceRoute(null)
    this.selectedRequest = null
    this.workspace = null
    this.reportCase = null
    this.reportCaseCompletionGate = null
    this.reportCaseContent = { evidence: [], findings: [], fragments: [] }
    this.stopPolling()
    await this.loadRequests()
  },
  async selectRequest(item, { updateRoute = true } = {}) {
    this.stopPolling()
    this.selectedRequest = item
    this.showInfoPanel = false
    this.infoReason = ''
    this.infoStepKey = ''
    this.workspaceSection = 'overview'
    this.selectedReportStepKey = ''
    if (updateRoute) this.syncWorkspaceRoute(item.id, 'overview', { history: 'push' })
    this.workspace = null
    this.reportCase = null
    this.reportCaseCompletionGate = null
    this.reportCaseContent = { evidence: [], findings: [], fragments: [] }
    this.reportAnalysisRuns = []
    this.message = ''
    this.$nextTick(() => {
      if (this.selectedRequest?.id === item.id) this.$el?.scrollTo?.(0, 0)
    })
    if (ownsRequest(item, this.staffActor)) await this.loadWorkspace(item.id)
  },
  async loadWorkspace(requestId) {
    this.loading = true
    try {
      this.workspace = await getStaffServiceRequestWorkspace(requestId)
      this.assignmentId = this.workspace.request.assigned_consultant_id ?? null
      this.consultationType = this.workspace.request.consultation_type || (
        this.workspace.request.service_type === 'report' ? 'integrated' : ''
      )
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
    const requestId = this.selectedRequest.id
    this.accepting = true
    try {
      await acceptStaffServiceRequest(requestId)
      if (this.scope === 'available') {
        this.scope = this.admin ? 'all' : 'mine'
        this.syncWorkspaceRoute(requestId, this.workspaceSection)
      }
      this.message = '申请已接收，完整资料已开放。'
      await this.loadRequests()
      await this.loadWorkspace(requestId)
    } catch (error) {
      this.message = this.errorText(error)
      await this.loadRequests()
    } finally {
      this.accepting = false
    }
  },
  openReleaseDialog() {
    if (!this.releaseSpecialty) return
    this.releaseDialog = { ...this.releaseDialog, visible: true, reason: '', error: '' }
  },
  async submitRelease() {
    if (!this.selectedRequest || this.releasing || !this.releaseSpecialty) return
    this.releasing = true
    try {
      await releaseStaffServiceRequest(
        this.selectedRequest.id,
        this.releaseSpecialty,
        this.releaseDialog.reason.trim() || null
      )
      this.releaseDialog = { ...this.releaseDialog, visible: false, reason: '', error: '' }
      this.message = '已退回当前专业。节点进度和已确认结果会保留，该专业重新进入待接单池。'
      await this.loadRequests()
      this.syncWorkspaceRoute(null)
      this.clearReportWorkspaceState()
    } catch (error) {
      this.releaseDialog = { ...this.releaseDialog, error: this.errorText(error) }
    } finally {
      this.releasing = false
    }
  }
}
