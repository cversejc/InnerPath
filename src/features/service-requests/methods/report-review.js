import { saveReportCaseFragment, resolveReportCaseQualityIssue, resolveReportCaseQualityIssueGroup } from '../../report-cases/api.js'
import { nextPendingRecord, reportFragmentReviewDraft } from '../../report-cases/review-continuation.js'
import { canHandleStep, specialtyLabels } from '../../report-cases/professional-ownership.js'

export default {
  repairReportFragmentSource(fragment) {
    if (this.reportReviewBusy) { this.message = '请先保存或取消本条修改，再修订来源。'; return }
    const snapshot = fragment.source_snapshot || {}
    const owners = []
    for (const [field, keyField] of [['findings', 'finding_key'], ['fragments', 'fragment_key']]) {
      for (const ref of snapshot[field] || []) {
        const current = this.reportCaseContent[field].find(row => row[keyField] === ref[keyField])
        if (current && (current.status !== 'CONFIRMED' || current.semantic_revision !== ref.semantic_revision)) owners.push(current.owner_step_task_id)
      }
    }
    const target = (this.reportCase.workflow_instance?.steps || []).filter(step =>
      step.status === 'COMPLETED' && (owners.includes(step.id) || (this.selectedReportStepKey === 'S6' && step.step_key === 'S5')))
      .sort((a, b) => a.sequence_no - b.sequence_no)[0]
    if (target) {
      this.reportStepReturn.targetStepKey = target.step_key
      this.reportStepReturn.reason = `复核“${this.fragmentTitle(fragment.fragment_key, fragment)}”的来源依据，修订后重新生成并审核相关报告内容。`
      this.reportStepReturn.visible = true
      this.setReportWorkspaceSection('overview')
      this.message = `已定位${this.reportStepLabel(target.step_key)}，请核对退回范围和原因后确认。`
    } else {
      this.nodeWritingMode = 'progress'
      this.setReportWorkspaceSection('writing')
      this.message = '已返回写作记录，请复核本段来源并重新生成待审版本。'
    }
  },
  beginReportFragmentReview() {
    if (this.reportReviewBusy) return
    const first = this.nodeFragments.find(item => item.status !== 'CONFIRMED') || this.nodeFragments[0]
    this.nodeRecordKeys.fragments = first?.fragment_key || ''
    this.setReportWorkspaceSection('fragments')
  },
  continueReportFragmentReview() {
    const next = nextPendingRecord(this.nodeFragments, this.nodeRecordKeys.fragments, 'fragment_key', row => row.status !== 'CONFIRMED')
    if (next) { this.nodeRecordKeys.fragments = next.fragment_key; this.scrollWorkspaceToTop() }
    else this.message = '当前正文已逐段确认。请复核全文连贯性与节点完成条件，再完成本节点。'
  },
  // S6 修改后稿件的整体确认：把本次修订的 REPORT 段落统一置为已确认，
  // 交付快照只会组装已确认段落，未确认的修订不能进入交付版本。
  async confirmReportManuscript() {
    if (!this.canEditSelectedReportStep || this.selectedReportStepKey !== 'S6' || this.reportFragmentSaving) {
      this.message = '当前节点暂时不能确认修改后稿件，请先开始最终审核节点。'; return
    }
    const pending = (this.reportCaseContent.fragments || [])
      .filter(item => item.fragment_type === 'REPORT' && item.status !== 'CONFIRMED')
    if (!pending.length) { this.message = '修改后的稿件已经全部确认，无需重复操作。'; return }
    if (pending.some(item => item.status === 'STALE')) {
      this.message = '有段落的来源依据已经更新，请先复核来源，再确认修改后稿件。'; return
    }
    const confirmed = await this.confirmAction({
      title: '确认修改后稿件',
      message: `将本次修订的 ${pending.length} 段正文确认为最终稿？确认后交付版本会使用这份稿件。`,
      confirmButtonText: '确认修改后稿件'
    })
    if (!confirmed) return
    this.reportFragmentSaving = true
    try {
      for (const fragment of pending) {
        await saveReportCaseFragment(this.reportCase.id, 'S6', fragment.fragment_key, {
          ...reportFragmentReviewDraft(fragment),
          status: 'CONFIRMED',
          edit_kind: 'STYLE'
        })
      }
      await this.loadReportCaseData(this.reportCase.id, { silent: true })
      this.message = '修改后的稿件已确认，可以完成最终复核并生成交付版本。'
    } catch (error) {
      const messages = {
        fragment_style_edit_changed_semantics: '确认失败：稿件在本次操作中发生变化，请刷新后重新确认。',
        fragment_revision_conflict: '正文已有新版本，已刷新列表，请重新通读后再确认。',
        report_fragment_source_stale: '本段依据已更新，请先复核前序成果。'
      }
      this.message = messages[error.response?.data?.detail] || this.errorText(error)
      if (error.response?.status === 409) {
        try { await this.loadReportCaseData(this.reportCase.id, { silent: true }) } catch { /* Preserve the original failure. */ }
      }
    } finally {
      this.reportFragmentSaving = false
    }
  },
  resumeGeneratedReportReview() {
    if (this.reportReviewAutoOpen && this.selectedReportStepKey === 'S5' && this.workspaceSection === 'writing'
      && this.nodeWritingMode === 'progress' && this.reportGeneration.status === 'READY_FOR_REVIEW' && !this.reportReviewBusy) {
      this.reportReviewAutoOpen = false
      this.beginReportFragmentReview()
    }
  },
  async saveReportFragmentReview({ fragment, review, onComplete }) {
    const finish = result => onComplete?.(result)
    if (!this.canEditSelectedReportStep || this.reportFragmentSaving || !['S5', 'S6'].includes(this.selectedReportStepKey)) {
      finish({ success: false, message: '当前节点暂时不能修订正文，请先开始本节点。' }); return
    }
    this.reportFragmentSaving = true
    let result
    try {
      await saveReportCaseFragment(this.reportCase.id, this.currentReportStep.step_key, fragment.fragment_key, review)
      await this.loadReportCaseData(this.reportCase.id, { silent: true })
      this.message = review.status === 'CONFIRMED' ? '本段审核已保存。' : '本段修改已保存，仍待确认。'
      result = { success: true }
    } catch (error) {
      const messages = {
        fragment_style_edit_changed_semantics: '本次修改涉及含义或审核状态，请选择“调整内容含义”再保存。',
        report_fragment_source_stale: '本段依据已更新，请先复核前序成果。',
        fragment_revision_conflict: '正文已有新版本，当前修改仍保留。请核对后取消修改、载入最新版。'
      }
      const message = messages[error.response?.data?.detail] || this.errorText(error)
      if (error.response?.status === 409) {
        try { await this.loadReportCaseData(this.reportCase.id, { silent: true }) } catch { /* Preserve the editor and original failure. */ }
      }
      this.message = message
      result = { success: false, message }
    } finally {
      this.reportFragmentSaving = false
      finish(result)
    }
  },
  async saveReportQualityReview({ issue, review, onComplete }) {
    const finish = result => onComplete?.(result)
    if (!this.canEditSelectedReportStep || this.selectedReportStepKey !== 'S6' || this.reportQualitySaving) {
      finish({ success: false, message: '当前节点暂时不能保存处理记录，请先开始最终审核节点。' }); return
    }
    this.reportQualitySaving = true
    let result
    try {
      await resolveReportCaseQualityIssue(this.reportCase.id, issue.id, review)
      await this.loadReportCaseData(this.reportCase.id, { silent: true })
      this.message = '本条问题处理记录已保存。'
      result = { success: true }
    } catch (error) {
      this.message = this.errorText(error)
      result = { success: false, message: this.message }
    } finally {
      this.reportQualitySaving = false
      finish(result)
    }
  },
  async saveReportQualityReviewGroup({ group, review, onComplete }) {
    const finish = result => onComplete?.(result)
    if (!this.canEditSelectedReportStep || this.selectedReportStepKey !== 'S6' || this.reportQualitySaving) {
      finish({ success: false, message: '当前节点暂时不能保存处理记录，请先开始最终审核节点。' }); return
    }
    this.reportQualitySaving = true
    let result
    try {
      await resolveReportCaseQualityIssueGroup(this.reportCase.id, review)
      await this.loadReportCaseData(this.reportCase.id, { silent: true })
      this.message = `已记录 ${group.count} 项同类问题的处理理由，每条问题仍单独留痕。`
      result = { success: true }
    } catch (error) {
      this.message = this.errorText(error)
      result = { success: false, message: this.message }
    } finally {
      this.reportQualitySaving = false
      finish(result)
    }
  },
  showNextReportStep(completedStep) {
    const next = this.currentReportStep
    if (next) {
      this.selectReportNode(next.step_key)
      const title = this.reportStepLabel(next.step_key)
      this.message = canHandleStep(next, this.staffActor)
        ? `${this.reportStepLabel(completedStep.step_key)}已完成，已进入${title}。点击“开始本节点”继续处理。`
        : `${this.reportStepLabel(completedStep.step_key)}已完成。下一步${title}由${specialtyLabels[next.required_capability] || '对应咨询师'}负责${next.assignee_id ? '，请由该负责人继续处理。' : '，当前待接单或分配。'}`
    } else this.message = '本节点已完成，请核对最终交付状态。'
  }
}
