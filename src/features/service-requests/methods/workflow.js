import {
  deliverStaffServiceRequest,
  getStaffServiceRequestTask,
  rejectAdminServiceRequest,
  requestStaffInfo,
  retryStaffAIDraft,
  saveStaffDraft,
  startStaffAIDraft
} from '../api.js'
import {
  buildCalendarPayload,
  buildReportPayload,
  calendarEditorFromPayload,
  reportEditorFromPayload
} from '../payloads.js'

export default {
  async startAI() {
    if (!this.workspace || this.aiStarting) return
    this.aiStarting = true
    try {
      const task = await startStaffAIDraft(this.workspace.request.id)
      this.task = task
      this.workspace.task = task
      this.message = 'AI 初稿已启动，完成后会出现在工作区。'
      this.startPolling(task)
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.aiStarting = false
    }
  },
  async regenerateAI() {
    if (!this.workspace || this.aiStarting) return
    if (!window.confirm('重新生成前会保存当前咨询师修改的版本快照，确定继续吗？')) return
    this.aiStarting = true
    try {
      const task = await retryStaffAIDraft(this.workspace.request.id, true)
      this.task = task
      this.workspace.task = task
      this.message = '已保存当前版本并重新启动 AI 初稿。'
      this.startPolling(task)
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.aiStarting = false
    }
  },
  startPolling(task) {
    this.stopPolling()
    if (!task?.task_id) return
    this.task = task
    this.pollingTask = true
    const tick = async () => {
      try {
        const updated = await getStaffServiceRequestTask(task.task_id)
        this.task = updated
        if (this.workspace) this.workspace.task = updated
        if (updated.status === 'processing') {
          this.pollTimer = window.setTimeout(tick, 1500)
        } else {
          this.pollingTask = false
          await this.loadWorkspace(this.workspace?.request?.id || task.request_id)
          this.message = updated.status === 'completed'
            ? 'AI 初稿已准备完成，请开始审校。'
            : 'AI 初稿生成失败，可在工作区重试。'
        }
      } catch (error) {
        this.pollingTask = false
        this.message = this.errorText(error)
      }
    }
    this.pollTimer = window.setTimeout(tick, 800)
  },
  stopPolling() {
    if (this.pollTimer) window.clearTimeout(this.pollTimer)
    this.pollTimer = null
    this.pollingTask = false
  },
  async saveDraft() {
    if (!this.workspace?.draft || this.saving) return
    this.saving = true
    try {
      const current = this.workspace.draft.editable_payload || {}
      const payload = this.workspace.request.service_type === 'report'
        ? buildReportPayload(current, this.reportEditor)
        : buildCalendarPayload(current, this.calendarEditor)
      const saved = await saveStaffDraft(
        this.workspace.request.id,
        payload,
        this.workspace.draft.content_version
      )
      this.workspace.draft = { ...this.workspace.draft, ...saved }
      this.workspace.request.status = 'reviewing'
      if (this.workspace.request.service_type === 'report') {
        this.reportEditor = reportEditorFromPayload(saved.editable_payload)
      } else {
        this.calendarEditor = calendarEditorFromPayload(saved.editable_payload)
      }
      this.message = '咨询师修改已保存。'
    } catch (error) {
      this.message = this.errorText(error)
      if (error.response?.status === 409) await this.loadWorkspace(this.workspace.request.id)
    } finally {
      this.saving = false
    }
  },
  async requestInfo() {
    if (!this.workspace || !this.infoReason || this.infoSaving) return
    this.infoSaving = true
    try {
      const updated = await requestStaffInfo(this.workspace.request.id, this.infoReason)
      this.workspace.request = { ...this.workspace.request, ...updated }
      this.message = '已标记为待用户补充，用户会在申请中心看到原因。'
      this.showInfoPanel = false
      this.infoReason = ''
      await this.loadRequests()
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.infoSaving = false
    }
  },
  async deliver() {
    if (!this.workspace || this.delivering) return
    if (!window.confirm('确认已完成人工审校并交付给用户吗？交付后申请和结果将进入只读状态。')) return
    this.delivering = true
    try {
      const updated = await deliverStaffServiceRequest(this.workspace.request.id)
      this.workspace.request = { ...this.workspace.request, ...updated }
      this.message = '申请已交付，用户现在可以查看最终结果。'
      await this.loadRequests()
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.delivering = false
    }
  },
  rejectRequest() {
    if (!this.admin || !this.workspace || this.rejectSaving) return
    this.rejectDialog = {
      visible: true,
      reason: '当前申请暂不具备处理条件',
      error: ''
    }
  },
  async submitReject() {
    if (!this.admin || !this.workspace || this.rejectSaving) return
    const reason = this.rejectDialog.reason.trim()
    if (!reason) {
      this.rejectDialog.error = '请输入关闭原因'
      return
    }
    this.rejectSaving = true
    try {
      const updated = await rejectAdminServiceRequest(this.workspace.request.id, reason)
      this.workspace.request = { ...this.workspace.request, ...updated }
      this.message = '申请已关闭，用户会在申请中心看到状态。'
      this.rejectDialog.visible = false
      await this.loadRequests()
    } catch (error) {
      this.rejectDialog.error = this.errorText(error)
      this.message = this.rejectDialog.error
    } finally {
      this.rejectSaving = false
    }
  }
}
