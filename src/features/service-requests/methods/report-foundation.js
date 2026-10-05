import {
  calculateReportCaseFoundation,
  correctReportCaseFoundation
} from '../../report-cases/api.js'

function foundationErrorMessage(error) {
  const code = error?.response?.data?.detail
  return {
    report_analysis_foundation_required: '出生资料不足，暂时无法生成测算。请回到上游输入核对出生日期、历法和性别。',
    report_foundation_revision_conflict: '测算依据已在其他操作中更新，请刷新当前节点后再修订。',
    report_foundation_value_invalid: '测算数据结构不完整，请保留包含 bazi 的完整 JSON。',
    report_foundation_version_invalid: '测算版本不匹配，请保留当前的 mingli-v2 标识。',
    report_foundation_correction_reason_required: '请填写修订原因后再保存。',
    report_analysis_step_not_current: '只有当前待处理的节点可以运行或修订测算。',
    report_analysis_step_not_in_review: '请先开始本节点，再运行或修订测算。'
  }[code] || '测算暂时无法保存，请检查当前节点状态后重试。'
}

export default {
  async calculateReportFoundation() {
    if (!this.reportCase || this.selectedReportStepKey !== 'S1' || !this.canEditSelectedReportStep || this.foundationSaving) return
    this.foundationSaving = true
    this.foundationError = ''
    try {
      await calculateReportCaseFoundation(this.reportCase.id, 'S1')
      await this.loadReportCaseData(this.reportCase.id)
      this.message = '程序测算已保存。请核对结果后再进入 AI 分析。'
    } catch (error) {
      this.foundationError = foundationErrorMessage(error)
      this.message = this.foundationError
    } finally {
      this.foundationSaving = false
    }
  },

  async correctReportFoundation({ value, reason }) {
    if (!this.reportCase || this.selectedReportStepKey !== 'S1' || !this.canEditSelectedReportStep || this.foundationSaving || !this.reportFoundationEvidence) return
    this.foundationSaving = true
    this.foundationError = ''
    try {
      await correctReportCaseFoundation(this.reportCase.id, 'S1', {
        expected_evidence_key: this.reportFoundationEvidence.evidence_key,
        value,
        reason
      })
      await this.loadReportCaseData(this.reportCase.id)
      this.message = '人工修订已保存为新证据版本。引用旧测算的判断已退回待审核，依赖它们的分析内容需要复核；后续 AI 分析会采用新版本。'
    } catch (error) {
      this.foundationError = foundationErrorMessage(error)
      this.message = this.foundationError
      if (error.response?.status === 409) await this.loadReportCaseData(this.reportCase.id)
    } finally {
      this.foundationSaving = false
    }
  }
}
