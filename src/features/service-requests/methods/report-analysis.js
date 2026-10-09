import {
  applyReportCaseAnalysisCandidates,
  applyReportCaseAnalysisFinding,
  applyReportCaseAnalysisFragment,
  saveReportCaseFinding,
  startReportCaseAnalysisDraft
} from '../../report-cases/api.js'

export default {
  async applyReportAnalysisCandidates({ run, onComplete }) {
    const finish = result => onComplete?.(result)
    if (!this.reportCase || !this.canEditSelectedReportStep || this.reportAnalysisFindingSavingKey || this.reportAnalysisFragmentSavingKey) {
      finish({ success: false, message: '当前节点暂时不能保存，请确认节点已开始处理。' })
      return
    }
    const savingKey = `${run.id}:batch`
    this.reportAnalysisFindingSavingKey = savingKey
    this.reportAnalysisFragmentSavingKey = savingKey
    try {
      const result = await applyReportCaseAnalysisCandidates(
        this.reportCase.id,
        this.currentReportStep.step_key,
        run.id
      )
      await this.loadReportCaseData(this.reportCase.id)
      const findingKey = result.finding_keys?.[0]
      const fragmentKey = result.fragment_keys?.[0]
      if (this.nodeRecordKeys) {
        if (findingKey) this.nodeRecordKeys.findings = findingKey
        if (fragmentKey) this.nodeRecordKeys.fragments = fragmentKey
      }
      this.setReportWorkspaceSection(findingKey ? 'findings' : 'fragments')
      this.message = `已加入待审内容：${result.finding_count} 条新判断、${result.fragment_count} 段新分析。请分别整体确认。`
      finish({ success: true, result })
    } catch (error) {
      const code = error.response?.data?.detail
      const messages = {
        report_analysis_candidate_not_found: '分析记录已不可用，请刷新后重新运行分析。',
        report_analysis_candidate_evidence_stale: '本次候选所依据的资料已更新，请重新运行 AI 分析。',
        report_analysis_candidate_dependency_cycle: '候选判断的相互引用存在循环，请调整分析要求并重新运行。',
        report_analysis_candidate_invalid: 'AI 候选结构不完整，请重新运行分析后再纳入。',
        report_analysis_candidates_empty: '本次运行没有可纳入的判断或分析内容。',
        report_analysis_fragment_findings_unconfirmed: '分析内容引用了当前无法采用的判断，请先处理判断后重新纳入。',
      }
      const message = error.response?.status === 409
        ? '本节点内容已发生变化，请刷新后核对最新版本。'
        : messages[code] || this.errorText(error)
      this.message = message
      finish({ success: false, message })
      if (error.response?.status === 409) await this.loadReportCaseData(this.reportCase.id)
    } finally {
      this.reportAnalysisFindingSavingKey = ''
      this.reportAnalysisFragmentSavingKey = ''
    }
  },

  async reviewReportAnalysisCandidate({ run, kind, candidate, review, expectedRevisionNo, onComplete }) {
    const finish = result => onComplete?.(result)
    if (!this.reportCase || !this.canEditSelectedReportStep || this.reportAnalysisFindingSavingKey || this.reportAnalysisFragmentSavingKey) {
      finish({ success: false, message: '当前节点暂时不能保存，请确认节点已开始处理。' })
      return
    }
    const isFinding = kind === 'finding'
    const key = candidate[isFinding ? 'finding_key' : 'fragment_key']
    const collection = this.reportCaseContent[isFinding ? 'findings' : 'fragments']
    const existing = collection.find(item => item[isFinding ? 'finding_key' : 'fragment_key'] === key)
    if (existing?.status === 'CONFIRMED') {
      const allowed = await this.confirmAction({ title: '修订已确认内容',
        message: '这项内容已经确认。保存会建立新版本，依赖它的分析和报告可能需要重新复核。', confirmButtonText: '保存修订' })
      if (!allowed) { finish({ success: false, message: '' }); return }
    }
    const savingField = isFinding ? 'reportAnalysisFindingSavingKey' : 'reportAnalysisFragmentSavingKey'
    this[savingField] = `${run.id}:${key}`
    let result
    try {
      const payload = JSON.parse(JSON.stringify(review))
      delete payload.expected_revision_no
      const hasCandidate = (run.output_parsed?.[isFinding ? 'findings' : 'analysis_fragments'] || [])
        .some(item => item[isFinding ? 'finding_key' : 'fragment_key'] === key)
      if (isFinding && !hasCandidate) {
        await saveReportCaseFinding(this.reportCase.id, this.currentReportStep.step_key, key,
          { ...payload, expected_revision_no: expectedRevisionNo, edit_kind: 'SEMANTIC' })
      } else {
        const apply = isFinding ? applyReportCaseAnalysisFinding : applyReportCaseAnalysisFragment
        await apply(this.reportCase.id, this.currentReportStep.step_key, run.id, key, {
          expected_revision_no: expectedRevisionNo,
          [isFinding ? 'finding_review' : 'fragment_review']: payload
        })
      }
      await this.loadReportCaseData(this.reportCase.id, { silent: true })
      this.message = isFinding ? (payload.status === 'REJECTED' ? '判断已拒绝，关联分析需核对并修订。' : '判断审核已保存。') : '分析内容已保存。'
      result = { success: true }
    } catch (error) {
      const code = error.response?.data?.detail
      const messages = {
        report_analysis_candidate_evidence_stale: '这次建议使用的资料已更新，请重新运行 AI 分析。',
        report_analysis_fragment_findings_unconfirmed: '仍有引用判断未确认，请先审核，或修订正文并移除不采用的引用。',
        report_analysis_fragment_support_required: '分析内容至少需要一条已确认判断或一项资料依据。',
        report_analysis_finding_support_required: '判断至少需要一项资料依据或一条关联判断。',
        framework_coverage_invalid: '覆盖依据摘句必须逐字出现在当前正文中，请检查摘句及覆盖说明。',
        framework_follow_up_required: '暂缓的分析需要填写待补充问题。',
        reasoning_analysis_details_required: '请补全推导说明的各项字段，再确认分析。',
        reasoning_period_source_mismatch: '阶段年份须采用当前程序计算中的大运起止年份。',
        reasoning_resource_reference_invalid: '请先确认行动引用的资源判断，再审核这条行动。',
        reasoning_block_reference_mismatch: '请核对行动与已确认卡点的关联。'
      }
      const message = error.response?.status === 409 ? '内容已被更新。请取消编辑并重新打开当前条目，核对最新版本。' : messages[code] || this.errorText(error)
      this.message = message
      result = { success: false, message }
      if (error.response?.status === 409) {
        try { await this.loadReportCaseData(this.reportCase.id, { silent: true }) } catch { /* Keep the review error visible. */ }
      }
    } finally {
      this[savingField] = ''
      finish(result || { success: false, message: '保存未完成，请重试。' })
    }
  },
  async startReportAnalysisDraft(feedbackRequest = null) {
    const step = this.currentReportStep
    if (!this.reportCase || !step || !['S1', 'S2', 'S3', 'S4'].includes(step.step_key) || step.status !== 'IN_REVIEW' || this.reportAnalysisPending) return
    const runtimeInstruction = typeof feedbackRequest === 'string'
      ? feedbackRequest
      : feedbackRequest?.runtimeInstruction || null
    const sourceRunId = typeof feedbackRequest === 'object'
      ? Number(feedbackRequest?.sourceRunId) || null
      : null
    const feedback = String(runtimeInstruction || '').trim()
    if (feedback.length > 4000) {
      this.message = '反馈不能超过 4000 个字符。'
      return
    }
    this.reportAnalysisSaving = true
    try {
      const activation = step.activation_no || 1
      await startReportCaseAnalysisDraft(this.reportCase.id, step.step_key, {
        idempotency_key: `case-${this.reportCase.id}-${step.step_key}-activation-${activation}-${globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`}`,
        runtime_instruction: feedback || null,
        source_run_id: feedback ? sourceRunId : null
      })
      await this.loadReportCaseData(this.reportCase.id)
      this.message = feedback
        ? `${this.reportStepLabel(step.step_key)}已收到反馈，正在按本次要求重新生成建议。`
        : `${this.reportStepLabel(step.step_key)}的分析建议已开始生成。`
    } catch (error) {
      this.message = error.response?.data?.detail === 'birth_time_confirmation_required'
        ? '请先完成“出生资料与时间核对”，再运行 S1 AI 分析。'
        : error.response?.data?.detail === 'report_analysis_foundation_required'
          ? '请先进入程序计算页保存并核对测算结果，再运行 S1 AI 分析。'
        : error.response?.data?.detail === 'report_analysis_feedback_source_stale'
          ? '之前的分析依据已更新。本次已停止沿用旧分析，请重新运行后再提交反馈。'
        : this.errorText(error)
      if (error.response?.status === 409) await this.loadReportCaseData(this.reportCase.id)
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
      const detail = error.response?.data?.detail
      this.message = detail === 'report_analysis_candidate_evidence_stale'
        ? '本次分析使用的资料版本已更新，请重新运行 AI 分析后再加入判断。'
        : error.response?.status === 409
          ? '专业判断已有更新，内容已刷新，请核对后再应用。'
          : this.errorText(error)
      if (error.response?.status === 409) await this.loadReportCaseData(this.reportCase.id)
    } finally {
      this.reportAnalysisFindingSavingKey = ''
    }
  },
  reviewAnalysisCandidateFindings({ findingKey }) {
    if (!this.nodeRecordKeys) return
    this.nodeRecordKeys.findings = findingKey || ''
    this.setReportWorkspaceSection('findings')
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
      const detail = error.response?.data?.detail
      this.message = detail === 'report_analysis_candidate_evidence_stale'
        ? '本次分析使用的资料版本已更新，请重新运行 AI 分析后再加入分析内容。'
        : detail === 'report_analysis_fragment_findings_unconfirmed'
          ? '这段分析引用的判断尚未全部确认。请先完成关联判断的审核，再返回这里加入分析内容。'
        : detail === 'reasoning_analysis_key_invalid'
          ? '这条分析建议的结构信息与当前节点不匹配。请刷新页面后重新运行 AI 分析，再加入待审核内容。'
        : error.response?.status === 409
          ? '分析内容已有更新，内容已刷新，请核对后再应用。'
          : this.errorText(error)
      if (error.response?.status === 409) await this.loadReportCaseData(this.reportCase.id)
    } finally {
      this.reportAnalysisFragmentSavingKey = ''
    }
  }
}
