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
      this.message = `${step.step_key} 分析草稿已进入运行队列。`
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
        title: '建立 Finding 新版本',
        message: '该判断已有已确认版本。应用此候选会建立新的待审核版本，并可能使依赖它的下游内容进入 STALE。',
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
      this.message = '候选判断已加入待审核 Finding，确认后才会进入正式语义。'
    } catch (error) {
      this.message = error.response?.status === 409
        ? 'Finding 已变化，内容已刷新，请核对后再应用。'
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
        title: '建立分析片段新版本',
        message: '该分析片段已有已确认版本。应用此候选会建立新的待审核版本，并使依赖旧语义的下游内容进入 STALE。',
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
      this.message = '候选片段已加入待审核内容。'
    } catch (error) {
      this.message = error.response?.status === 409
        ? '分析片段已变化，内容已刷新，请核对后再应用。'
        : this.errorText(error)
      if (error.response?.status === 409) await this.loadReportCaseData(this.reportCase.id)
    } finally {
      this.reportAnalysisFragmentSavingKey = ''
    }
  }
}
