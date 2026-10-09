import {
  completeSimpleReportCaseStep,
  getSimpleReportCaseVersions,
  startReportCaseStep
} from '../../report-cases/api.js'
import { simpleReportVersionLabel } from '../../report-cases/simple-stages.js'

// Sidecar for `report.simple`: the simplified workflow only ever exchanges the
// application snapshot plus the current full report text. It deliberately does
// not read the production content, narrative, quality or skill-run resources.
export default {
  async loadSimpleReportCaseData(caseId) {
    this.simpleReportLoading = true
    try {
      const versions = await getSimpleReportCaseVersions(caseId)
      this.simpleReportVersions = [...(versions.items || [])].sort(
        (left, right) => left.version_no - right.version_no
      )
      const stepKey = this.selectedReportStepKey || this.currentReportStep?.step_key || ''
      // Force a re-seed when the current draft is still empty: route restoration
      // syncs before the versions arrive, so the upstream text may be missing.
      // Non-empty drafts are left alone to keep the consultant's edits.
      this.syncSimpleReportDraft(stepKey, !this.simpleReportDraft?.report_text)
    } catch (error) {
      this.message = this.errorText(error)
      throw error
    } finally {
      this.simpleReportLoading = false
    }
  },
  resetSimpleReportState() {
    this.simpleReportLoading = false
    this.simpleReportSaving = false
    this.simpleReportVersions = []
    this.simpleReportDraft = null
  },
  selectSimpleReportStep(stepKey) {
    if (this.reportReviewBusy) { this.message = '请先保存或取消当前修改，再切换节点。'; return }
    if (stepKey && !this.simpleReportStep(stepKey)) return
    this.selectedReportStepKey = stepKey
    this.syncSimpleReportDraft(stepKey)
    if (this.selectedRequest) this.syncWorkspaceRoute(this.selectedRequest.id, 'overview', { history: 'push' })
    this.scrollWorkspaceToTop()
  },
  simpleReportStep(stepKey) {
    return (this.reportCase?.workflow_instance?.steps || []).find(step => step.step_key === stepKey) || null
  },
  simpleReportOutputVersion(step) {
    const configured = Number(step?.config_snapshot?.output_version)
    if (Number.isFinite(configured) && configured > 0) return configured
    const sequence = Number(step?.sequence_no)
    return Number.isFinite(sequence) && sequence > 0 ? sequence : 0
  },
  // Round N starts from the full text of round N-1. Anything else could feed a
  // later revision backwards when a consultant reopens a node.
  simpleReportUpstreamVersion(step) {
    const upstreamNo = this.simpleReportOutputVersion(step) - 1
    if (upstreamNo < 1) return null
    return this.simpleReportVersions.find(version => version.version_no === upstreamNo) || null
  },
  simpleReportNextStepKey(stepKey) {
    const steps = this.reportCase?.workflow_instance?.steps || []
    const current = steps.find(step => step.step_key === stepKey)
    if (!current) return ''
    return steps.find(step => step.sequence_no === current.sequence_no + 1)?.step_key || ''
  },
  restoreSimpleReportNode(query = this.$route.query) {
    const steps = this.reportCase?.workflow_instance?.steps || []
    const requested = String(query?.step || '').trim()
    const requestedStep = steps.find(step => step.step_key === requested)
    const current = this.currentReportStep
    // `all` deliberately opens the simplified overview; anything unknown falls
    // back to the active round so the consultant always lands on real work.
    this.selectedReportStepKey = requested === 'all'
      ? ''
      : (requestedStep || current)?.step_key || ''
    this.workspaceSection = 'overview'
    this.syncSimpleReportDraft(this.selectedReportStepKey)
  },
  syncSimpleReportDraft(stepKey = this.currentReportStep?.step_key || '', force = false) {
    const normalizedStepKey = String(stepKey || '')
    const draft = this.simpleReportDraft || {}
    // Keep the consultant's in-progress text when the node does not change.
    if (!force && draft.step_key === normalizedStepKey) return
    const upstream = this.simpleReportUpstreamVersion(this.simpleReportStep(normalizedStepKey))
    this.simpleReportDraft = {
      step_key: normalizedStepKey,
      report_text: upstream?.report_text || '',
      review_note: '',
      final_gate_confirmed: false
    }
  },
  async startSimpleReportStep() {
    const step = this.currentReportStep
    if (!this.reportCase || !step || this.simpleReportSaving) return
    this.simpleReportSaving = true
    try {
      await startReportCaseStep(this.reportCase.id, step.step_key)
      await this.loadReportCaseData(this.reportCase.id, { silent: true })
      this.message = `已开始${this.reportStepLabel(step.step_key)}，请核对申请资料后提交本轮完整报告。`
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.simpleReportSaving = false
    }
  },
  async completeSimpleReportStep() {
    const step = this.currentReportStep
    const draft = this.simpleReportDraft || {}
    if (!this.reportCase || !step || this.simpleReportSaving) return
    if (draft.step_key !== step.step_key) {
      this.message = '报告草稿与当前节点不一致，请刷新后继续。'
      return
    }
    const reportText = String(draft.report_text || '').trim()
    if (!reportText) {
      this.message = '请先填写本轮完整报告文本，再完成本节点。'
      return
    }
    const isFinal = step.config_snapshot?.final_gate === true
    if (isFinal && !draft.final_gate_confirmed) {
      this.message = '请先确认已完成最终终审，再提交交付。'
      return
    }
    const versionLabel = simpleReportVersionLabel(step)
    const confirmed = await this.confirmAction({
      title: isFinal ? '提交最终报告' : `完成${this.reportStepLabel(step.step_key)}`,
      message: isFinal
        ? `提交后将保存 ${versionLabel} 终稿并交付给用户，交付后版本不可覆盖。`
        : `将本轮完整报告保存为 ${versionLabel}，并流转到下一节点继续修改。`,
      confirmButtonText: isFinal ? '确认交付' : '保存并进入下一节点'
    })
    if (!confirmed) return
    const caseId = this.reportCase.id
    this.simpleReportSaving = true
    try {
      const result = await completeSimpleReportCaseStep(caseId, step.step_key, {
        report_text: reportText,
        review_note: String(draft.review_note || '').trim() || null,
        final_gate_confirmed: isFinal
      })
      if (result?.delivered && this.workspace?.request?.id) {
        await this.loadWorkspace(this.workspace.request.id)
        this.message = `报告 ${result.version?.version_label || versionLabel} 已交付给用户。`
      } else {
        const nextStepKey = this.simpleReportNextStepKey(step.step_key)
        await this.loadReportCaseData(caseId, { silent: true })
        if (nextStepKey) {
          this.selectedReportStepKey = nextStepKey
          this.syncSimpleReportDraft(nextStepKey, true)
          if (this.selectedRequest) this.syncWorkspaceRoute(this.selectedRequest.id, 'overview', { history: 'replace' })
          this.scrollWorkspaceToTop()
        }
        this.message = `${result?.version?.version_label || versionLabel} 已保存，请继续下一节点。`
      }
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.simpleReportSaving = false
    }
  }
}
