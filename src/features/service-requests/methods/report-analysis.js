import {
  applyReportCaseAnalysisFinding,
  applyReportCaseAnalysisFragment,
  startReportCaseAnalysisDraft
} from '../../report-cases/api.js'

export default {
  async startReportAnalysisDraft() {
    const step = this.currentReportStep
    if (!this.reportCase || !step || !['S1', 'S2', 'S3', 'S4'].includes(step.step_key) || step.status !== 'IN_REVIEW' || this.reportAnalysisSaving) return
    this.reportAnalysisSaving = true
    try {
      const activation = step.activation_no || 1
      await startReportCaseAnalysisDraft(this.reportCase.id, step.step_key, {
        idempotency_key: `case-${this.reportCase.id}-${step.step_key}-activation-${activation}-${Date.now()}`
      })
      await this.loadReportCaseData(this.reportCase.id)
      this.message = `${this.reportStepLabel(step.step_key)}的分析建议已开始生成。`
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.reportAnalysisSaving = false
    }
  },
  async applyReportAnalysisFinding({ run, candidate, expectedRevisionNo }) {
    if (!this.reportCase || !this.currentReportStep || this.reportAnalysisFindingSavingKey) return
    const existing = this.reportCaseContent.findings.find(item => item.finding_key === candidate.finding_key)
    if (existing?.source_skill_run_id === run.id) return
    if (existing?.status === 'CONFIRMED') {
      const confirmed = await this.confirmAction({
        title: '更新已确认的专业判断',
        message: '这条判断已有确认版本。采用新建议会建立待审核版本，相关报告内容之后需要重新检查。',
        confirmButtonText: '建立新版本'
      })
      if (!confirmed) return
    }
    this.reportAnalysisFindingSavingKey = `${run.id}:${candidate.finding_key}`
    try {
      await applyReportCaseAnalysisFinding(
        this.reportCase.id,
        this.currentReportStep.step_key,
        run.id,
        candidate.finding_key,
        { expected_revision_no: expectedRevisionNo }
      )
      await this.loadReportCaseData(this.reportCase.id)
      if (this.nodeRecordKeys) {
        this.nodeRecordKeys.findings = candidate.finding_key
        this.setReportWorkspaceSection('findings')
      }
      this.message = '建议判断已加入待审核列表，请修改、接受或拒绝；确认后才会用于后续报告。'
    } catch (error) {
      this.message = error.response?.status === 409
        ? '专业判断已有更新，内容已刷新，请核对后再应用。'
        : this.errorText(error)
      if (error.response?.status === 409) await this.loadReportCaseData(this.reportCase.id)
    } finally {
      this.reportAnalysisFindingSavingKey = ''
    }
  },
  async applyReportAnalysisFragment({ run, candidate, expectedRevisionNo }) {
    if (!this.reportCase || !this.currentReportStep || this.reportAnalysisFragmentSavingKey) return
    const existing = this.reportCaseContent.fragments.find(item => item.fragment_key === candidate.fragment_key)
    if (existing?.source_skill_run_id === run.id) return
    if (existing?.status === 'CONFIRMED') {
      const confirmed = await this.confirmAction({
        title: '更新已确认的分析内容',
        message: '这段内容已有确认版本。采用新建议会建立待审核版本，相关报告内容之后需要重新检查。',
        confirmButtonText: '建立新版本'
      })
      if (!confirmed) return
    }
    this.reportAnalysisFragmentSavingKey = `${run.id}:${candidate.fragment_key}`
    try {
      await applyReportCaseAnalysisFragment(
        this.reportCase.id,
        this.currentReportStep.step_key,
        run.id,
        candidate.fragment_key,
        { expected_revision_no: expectedRevisionNo }
      )
      await this.loadReportCaseData(this.reportCase.id)
      if (this.nodeRecordKeys) {
        this.nodeRecordKeys.fragments = candidate.fragment_key
        this.setReportWorkspaceSection('fragments')
      }
      this.message = '建议内容已加入待审核列表，请审阅并确认。'
    } catch (error) {
      this.message = error.response?.status === 409
        ? '分析内容已有更新，内容已刷新，请核对后再应用。'
        : this.errorText(error)
      if (error.response?.status === 409) await this.loadReportCaseData(this.reportCase.id)
    } finally {
      this.reportAnalysisFragmentSavingKey = ''
    }
  }
}
