import {
  completeReportCaseStep,
  confirmReportCaseNarrativePlan,
  approveReportCaseFinalGate,
  deliverReportCase,
  generateReportCaseFragment,
  generateReportNarrativeCandidates,
  getReportCase,
  getReportCaseContent,
  getReportCaseNarrative,
  getReportCaseQuality,
  getReportCaseStepCompletionGate,
  reopenReportCaseStep,
  resolveReportCaseQualityIssue,
  returnReportCaseStep,
  runReportCaseCoherenceCheck,
  runReportCaseQuality,
  saveReportCaseFinding,
  saveReportCaseFragment,
  startReportCaseGeneration,
  startReportCaseStep
} from '../../report-cases/api.js'
import { getCaseSkillRuns } from '../../skills/api.js'

function splitReferences(value) {
  return String(value || '')
    .split(/[\n,，]/)
    .map(item => item.trim())
    .filter(Boolean)
}

export default {
  async loadReportCaseData(caseId) {
    this.reportCaseLoading = true
    if (this.reportNarrativePollTimer) {
      clearTimeout(this.reportNarrativePollTimer)
      this.reportNarrativePollTimer = null
    }
    try {
      const [reportCase, content, narrative, quality, analysisRuns] = await Promise.all([
        getReportCase(caseId),
        getReportCaseContent(caseId),
        getReportCaseNarrative(caseId),
        getReportCaseQuality(caseId),
        getCaseSkillRuns(caseId)
      ])
      this.reportCase = reportCase
      this.reportCaseContent = content
      this.reportNarrative = narrative
      this.reportQuality = quality
      this.reportAnalysisRuns = analysisRuns
      const activeStep = (reportCase.workflow_instance?.steps || []).find(step =>
        ['READY', 'IN_REVIEW', 'EXECUTING', 'WAITING_REVIEW'].includes(step.status)
      )
      this.reportCaseCompletionGate = activeStep?.status === 'IN_REVIEW'
        && ['S1', 'S2', 'S3', 'S4'].includes(activeStep.step_key)
        ? await getReportCaseStepCompletionGate(reportCase.id, activeStep.step_key)
        : null
      this.reportQualityIssueDrafts = Object.fromEntries(
        quality.issues
          .filter(issue => issue.status === 'OPEN')
          .map(issue => [issue.id, {
            status: issue.severity === 'BLOCK' ? 'RESOLVED' : 'ACCEPTED',
            resolution: ''
          }])
      )
      this.reportFragmentDrafts = Object.fromEntries(
        content.fragments.map(fragment => [fragment.fragment_key, {
          revision_no: fragment.revision_no,
          title: fragment.title || '',
          content: fragment.content,
          status: fragment.status === 'STALE' ? 'PROPOSED' : fragment.status,
          fragment_type: fragment.fragment_type,
          edit_kind: fragment.status === 'STALE' ? 'SEMANTIC' : 'STYLE',
          finding_refs: (fragment.source_snapshot?.findings || []).map(item => item.finding_key).join('\n'),
          fragment_refs: (fragment.source_snapshot?.fragments || []).map(item => item.fragment_key).join('\n'),
          evidence_refs: (fragment.source_snapshot?.evidence || []).map(item => item.evidence_key).join('\n')
        }])
      )
      const steps = reportCase.workflow_instance?.steps || []
      const active = steps.find(step => ['READY', 'IN_REVIEW', 'EXECUTING', 'WAITING_REVIEW'].includes(step.status))
      this.reportStepReturn.targetStepKey = steps.find(step => step.sequence_no < (active?.sequence_no || Infinity) && step.status === 'COMPLETED')?.step_key || ''
      for (const run of narrative.candidate_runs || []) {
        for (const candidate of run.output_parsed?.candidates || []) {
          const draftKey = this.narrativeDraftKey(run, candidate)
          if (!this.narrativeCandidateDrafts[draftKey]) {
            this.narrativeCandidateDrafts[draftKey] = {
              core_theme: this.consultantText(candidate.theme, ''),
              must_include_findings: [...(candidate.supporting_findings || [])],
              self_direction: ''
            }
          }
        }
      }
      this.scheduleNarrativePoll(caseId)
    } catch (error) {
      this.message = this.errorText(error)
      throw error
    } finally {
      this.reportCaseLoading = false
    }
  },
  narrativeDraftKey(run, candidate) {
    return `${run.id}:${candidate.candidate_key}`
  },
  scheduleNarrativePoll(caseId) {
    const runs = [
      ...(this.reportNarrative.candidate_runs || []),
      ...(this.reportNarrative.fragment_runs || []),
      ...(this.reportAnalysisRuns || []),
      ...(this.reportQuality.latest_validator_run ? [this.reportQuality.latest_validator_run] : [])
    ]
    const generationRunning = [
      'IN_PROGRESS',
      'CHAPTER_COHERENCE_CHECK',
      'COHERENCE_CHECK'
    ].includes(
      this.reportNarrative.current_plan?.plan_json?.generation?.status
    )
    if (!generationRunning && !runs.some(run => ['PENDING', 'RUNNING'].includes(run.status))) return
    this.reportNarrativePollTimer = setTimeout(async () => {
      if (this.reportCase?.id !== caseId) return
      try {
        const [content, narrative, quality, analysisRuns] = await Promise.all([
          getReportCaseContent(caseId),
          getReportCaseNarrative(caseId),
          getReportCaseQuality(caseId),
          getCaseSkillRuns(caseId)
        ])
        this.reportCaseContent = content
        this.reportNarrative = narrative
        this.reportQuality = quality
        this.reportAnalysisRuns = analysisRuns
        const activeStep = (this.reportCase?.workflow_instance?.steps || []).find(step =>
          ['READY', 'IN_REVIEW', 'EXECUTING', 'WAITING_REVIEW'].includes(step.status)
        )
        this.reportCaseCompletionGate = activeStep?.status === 'IN_REVIEW'
          && ['S1', 'S2', 'S3', 'S4'].includes(activeStep.step_key)
          ? await getReportCaseStepCompletionGate(caseId, activeStep.step_key)
          : null
        this.reportQualityIssueDrafts = Object.fromEntries(
          quality.issues
            .filter(issue => issue.status === 'OPEN')
            .map(issue => [issue.id, {
              status: issue.severity === 'BLOCK' ? 'RESOLVED' : 'ACCEPTED',
              resolution: ''
            }])
        )
        const refreshedDrafts = Object.fromEntries(
          content.fragments.map(fragment => [fragment.fragment_key, {
            revision_no: fragment.revision_no,
            title: fragment.title || '',
            content: fragment.content,
            status: fragment.status === 'STALE' ? 'PROPOSED' : fragment.status,
            fragment_type: fragment.fragment_type,
            edit_kind: fragment.status === 'STALE' ? 'SEMANTIC' : 'STYLE',
            finding_refs: (fragment.source_snapshot?.findings || []).map(item => item.finding_key).join('\n'),
            fragment_refs: (fragment.source_snapshot?.fragments || []).map(item => item.fragment_key).join('\n'),
            evidence_refs: (fragment.source_snapshot?.evidence || []).map(item => item.evidence_key).join('\n')
          }])
        )
        for (const fragment of content.fragments) {
          const current = this.reportFragmentDrafts[fragment.fragment_key]
          if (!current || current.revision_no !== fragment.revision_no) {
            this.reportFragmentDrafts[fragment.fragment_key] = refreshedDrafts[fragment.fragment_key]
          }
        }
        for (const run of narrative.candidate_runs || []) {
          for (const candidate of run.output_parsed?.candidates || []) {
            const draftKey = this.narrativeDraftKey(run, candidate)
            if (!this.narrativeCandidateDrafts[draftKey]) {
              this.narrativeCandidateDrafts[draftKey] = {
                core_theme: this.consultantText(candidate.theme, ''),
                must_include_findings: [...(candidate.supporting_findings || [])],
                self_direction: ''
              }
            }
          }
        }
        this.scheduleNarrativePoll(caseId)
      } catch (error) {
        this.message = this.errorText(error)
      }
    }, 1800)
  },
  async runReportQuality() {
    if (!this.reportCase || this.reportQualitySaving) return
    this.reportQualitySaving = true
    try {
      this.reportQuality = await runReportCaseQuality(this.reportCase.id, {
        idempotency_key: `case-${this.reportCase.id}-qa-${Date.now()}`
      })
      this.scheduleNarrativePoll(this.reportCase.id)
      this.message = this.reportQuality.quality_status === 'PROGRAMMATIC_BLOCKED'
        ? '交付前检查发现必须处理的问题，请先修订报告内容。'
        : '交付前检查已开始。'
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.reportQualitySaving = false
    }
  },
  async resolveReportQualityIssue(issue) {
    const draft = this.reportQualityIssueDrafts[issue.id]
    if (!this.reportCase || !draft?.resolution?.trim() || this.reportQualitySaving) return
    this.reportQualitySaving = true
    try {
      await resolveReportCaseQualityIssue(this.reportCase.id, issue.id, {
        status: draft.status,
        resolution: draft.resolution.trim()
      })
      await this.loadReportCaseData(this.reportCase.id)
      this.message = '交付前问题处理记录已保存。'
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.reportQualitySaving = false
    }
  },
  async approveReportFinalGate() {
    if (!this.reportCase || !this.finalGateAttested || this.reportStepSaving) return
    const confirmed = await this.confirmAction({
      title: '确认最终复核',
      message: '确认已复核报告主线、用户贴合度与所有检查问题，并承担最终交付责任？',
      confirmButtonText: '确认并完成'
    })
    if (!confirmed) return
    this.reportStepSaving = true
    try {
      await approveReportCaseFinalGate(this.reportCase.id, {
        attested: true,
        note: null
      })
      this.finalGateAttested = false
      await this.loadReportCaseData(this.reportCase.id)
      this.message = '最终复核已通过，可以生成交付版本。'
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.reportStepSaving = false
    }
  },
  async deliverReportCaseVersion() {
    if (!this.reportCase || this.reportCaseDelivering) return
    const confirmed = await this.confirmAction({
      title: '交付报告版本',
      message: '将当前已通过最终门禁的报告快照交付给用户？交付后版本不可覆盖。',
      confirmButtonText: '生成并交付'
    })
    if (!confirmed) return
    this.reportCaseDelivering = true
    try {
      const version = await deliverReportCase(this.reportCase.id)
      await this.loadWorkspace(this.workspace.request.id)
      this.message = `报告 v${version.version_no} 已交付，用户现在可以查看。`
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.reportCaseDelivering = false
    }
  },
  async generateNarrativeCandidates() {
    const step = this.currentReportStep
    if (!this.reportCase || !step || step.status !== 'IN_REVIEW' || this.reportNarrativeSaving) return
    this.reportNarrativeSaving = true
    try {
      await generateReportNarrativeCandidates(this.reportCase.id, step.step_key, {
        idempotency_key: `case-${this.reportCase.id}-narrative-${Date.now()}`
      })
      await this.loadReportCaseData(this.reportCase.id)
      this.message = '报告主线建议已开始生成。'
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.reportNarrativeSaving = false
    }
  },
  async confirmNarrativeCandidate(run, candidate) {
    const draft = this.narrativeCandidateDrafts[this.narrativeDraftKey(run, candidate)] || {}
    if (!this.reportCase || this.reportNarrativeSaving) return
    const coreTheme = String(draft.core_theme || '').trim()
    if (!coreTheme || !this.consultantText(coreTheme, '')) {
      this.message = '请使用中文补充报告主线，再确认此方案。'
      return
    }
    const confirmed = await this.confirmAction({
      title: '确认叙事方案',
      message: `将“${coreTheme}”确认为当前报告主线？`,
      confirmButtonText: '确认方案'
    })
    if (!confirmed) return
    this.reportNarrativeSaving = true
    try {
      await confirmReportCaseNarrativePlan(this.reportCase.id, {
        skill_run_id: run.id,
        candidate_key: candidate.candidate_key,
        overrides: {
          core_theme: coreTheme,
          must_include_findings: draft.must_include_findings || candidate.supporting_findings || [],
          self_direction: draft.self_direction || null
        }
      })
      await this.loadReportCaseData(this.reportCase.id)
      this.message = '报告主线已确认并保存。'
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.reportNarrativeSaving = false
    }
  },
  async generateCompleteReport() {
    if (!this.reportCase || this.reportNarrativeSaving) return
    this.reportNarrativeSaving = true
    try {
      await startReportCaseGeneration(this.reportCase.id, {
        idempotency_key: `case-${this.reportCase.id}-generation-${Date.now()}`
      })
      await this.loadReportCaseData(this.reportCase.id)
      this.message = '报告内容已开始按顺序生成。'
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.reportNarrativeSaving = false
    }
  },
  async runReportCoherenceCheck() {
    if (!this.reportCase || this.reportNarrativeSaving) return
    this.reportNarrativeSaving = true
    try {
      const run = await runReportCaseCoherenceCheck(this.reportCase.id, {
        idempotency_key: `case-${this.reportCase.id}-coherence-${Date.now()}`
      })
      await this.loadReportCaseData(this.reportCase.id)
      this.message = run.target_type === 'REPORT_CHAPTER_COHERENCE'
        ? '当前章节的连贯性检查已开始。'
        : '整篇报告的连贯性检查已开始。'
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.reportNarrativeSaving = false
    }
  },
  async generateReportFragment() {
    const step = this.currentReportStep
    const draft = this.newReportWritingFragment
    if (!this.reportCase || !step || step.status !== 'IN_REVIEW' || !draft.fragment_key.trim() || this.reportNarrativeSaving) return
    this.reportNarrativeSaving = true
    try {
      await generateReportCaseFragment(this.reportCase.id, step.step_key, {
        idempotency_key: `case-${this.reportCase.id}-fragment-${Date.now()}`,
        fragment_key: draft.fragment_key.trim(),
        title: draft.title.trim() || null
      })
      this.newReportWritingFragment = { fragment_key: '', title: '' }
      await this.loadReportCaseData(this.reportCase.id)
      this.message = '报告内容已开始生成。'
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.reportNarrativeSaving = false
    }
  },
  async startReportStep() {
    const step = this.currentReportStep
    if (!this.reportCase || !step || this.reportStepSaving) return
    this.reportStepSaving = true
    try {
      await startReportCaseStep(this.reportCase.id, step.step_key)
      await this.loadReportCaseData(this.reportCase.id)
      this.message = `已开始${this.reportStepLabel(step.step_key)}，可以查看并处理相关内容。`
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.reportStepSaving = false
    }
  },
  async completeReportStep() {
    const step = this.currentReportStep
    if (!this.reportCase || !step || this.reportStepSaving) return
    const confirmed = await this.confirmAction({
      title: '完成当前步骤',
      message: '确认已完成当前步骤的人工审核？下一步骤将被激活。',
      confirmButtonText: '完成步骤'
    })
    if (!confirmed) return
    this.reportStepSaving = true
    try {
      await completeReportCaseStep(this.reportCase.id, step.step_key, {
        reviewed_finding_count: this.reportCaseContent.findings.length,
        reviewed_fragment_count: this.reportCaseContent.fragments.length
      })
      await this.loadReportCaseData(this.reportCase.id)
      this.message = '当前步骤已完成。'
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.reportStepSaving = false
    }
  },
  async submitReportStepReturn() {
    const step = this.currentReportStep
    const { targetStepKey, reason } = this.reportStepReturn
    if (!this.reportCase || !step || !targetStepKey || !reason.trim() || this.reportStepSaving) return
    this.reportStepSaving = true
    try {
      await returnReportCaseStep(this.reportCase.id, step.step_key, targetStepKey, reason.trim())
      this.reportStepReturn.visible = false
      this.reportStepReturn.reason = ''
      await this.loadReportCaseData(this.reportCase.id)
      this.message = '步骤已退回，目标步骤重新激活。'
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.reportStepSaving = false
    }
  },
  async reopenReportStep(step) {
    if (!this.reportCase || this.reportStepSaving) return
    this.reportStepSaving = true
    try {
      await reopenReportCaseStep(this.reportCase.id, step.step_key)
      await this.loadReportCaseData(this.reportCase.id)
      this.message = `${this.reportStepLabel(step.step_key)}已重新打开。`
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.reportStepSaving = false
    }
  },
  editReportFinding(finding) {
    this.editingFindingKey = finding.finding_key
    this.reportFindingDraft = {
      finding_key: finding.finding_key,
      expected_revision_no: finding.revision_no,
      claim: finding.claim,
      kind: finding.kind,
      semantic_role: finding.semantic_role,
      confidence: finding.confidence,
      importance: finding.importance,
      reportability: finding.reportability,
      status: finding.status,
      evidence_refs: [...(finding.evidence_refs || [])].join('\n'),
      relation_refs: structuredClone(finding.relation_refs || []),
      structured_data: structuredClone(finding.structured_data_json || {}),
      edit_kind: 'SEMANTIC'
    }
  },
  async setReportFindingStatus(finding, status) {
    this.editReportFinding(finding)
    this.reportFindingDraft.status = status
    await this.saveReportFinding()
  },
  async saveReportFinding() {
    const draft = this.reportFindingDraft
    const step = this.currentReportStep
    if (!this.reportCase || !step || !draft?.claim.trim() || !draft.semantic_role.trim() || this.reportFindingSaving) return
    this.reportFindingSaving = true
    try {
      const { finding_key: key, ...payload } = draft
      payload.evidence_refs = splitReferences(payload.evidence_refs)
      await saveReportCaseFinding(this.reportCase.id, step.step_key, key, payload)
      this.editingFindingKey = null
      await this.loadReportCaseData(this.reportCase.id)
      this.message = '专业判断的新版本已保存。'
    } catch (error) {
      this.message = error.response?.status === 409
        ? '专业判断已被其他人更新，内容已刷新，请确认后再编辑。'
        : this.errorText(error)
      if (error.response?.status === 409) await this.loadReportCaseData(this.reportCase.id)
    } finally {
      this.reportFindingSaving = false
    }
  },
  async addReportFinding() {
    const draft = this.newReportFinding
    const step = this.currentReportStep
    if (!this.reportCase || !step || !draft.claim.trim() || this.reportFindingSaving) return
    this.reportFindingSaving = true
    try {
      const findingKey = draft.finding_key.trim() || `consultant.added_${Date.now()}`
      await saveReportCaseFinding(this.reportCase.id, step.step_key, findingKey, {
        expected_revision_no: null,
        claim: draft.claim.trim(),
        kind: 'FINDING',
        semantic_role: draft.semantic_role.trim() || 'OBSERVATION',
        confidence: 'MEDIUM',
        importance: 'MEDIUM',
        reportability: 'OPTIONAL',
        status: 'PROPOSED',
        evidence_refs: splitReferences(draft.evidence_refs),
        relation_refs: [],
        structured_data: {},
        edit_kind: 'SEMANTIC'
      })
      this.newReportFinding = { finding_key: '', claim: '', semantic_role: 'OBSERVATION', evidence_refs: '' }
      await this.loadReportCaseData(this.reportCase.id)
      this.message = '新增的专业判断已加入待审核列表。'
    } catch (error) {
      this.message = error.response?.status === 409
        ? '这条专业判断已存在，列表已刷新。'
        : this.errorText(error)
      if (error.response?.status === 409) await this.loadReportCaseData(this.reportCase.id)
    } finally {
      this.reportFindingSaving = false
    }
  },
  async saveReportFragment(fragment) {
    const step = this.currentReportStep
    const draft = this.reportFragmentDrafts[fragment.fragment_key]
    if (!this.reportCase || !step || !draft.content.trim() || this.reportFragmentSaving) return
    this.reportFragmentSaving = true
    try {
      await saveReportCaseFragment(this.reportCase.id, step.step_key, fragment.fragment_key, {
        expected_revision_no: fragment.revision_no,
        fragment_type: draft.fragment_type,
        title: draft.title,
        content: draft.content,
        status: draft.status,
        finding_refs: splitReferences(draft.finding_refs),
        fragment_refs: splitReferences(draft.fragment_refs),
        evidence_refs: splitReferences(draft.evidence_refs),
        edit_kind: fragment.status === draft.status ? draft.edit_kind : 'SEMANTIC'
      })
      await this.loadReportCaseData(this.reportCase.id)
      this.message = '报告内容的新版本已保存。'
    } catch (error) {
      this.message = error.response?.status === 409
        ? '报告内容已被其他人更新，内容已刷新，请确认后再编辑。'
        : this.errorText(error)
      if (error.response?.status === 409) await this.loadReportCaseData(this.reportCase.id)
    } finally {
      this.reportFragmentSaving = false
    }
  },
  async addReportFragment() {
    const draft = this.newReportFragment
    const step = this.currentReportStep
    if (!this.reportCase || !step || !draft.content.trim() || this.reportFragmentSaving) return
    this.reportFragmentSaving = true
    try {
      const fragmentKey = draft.fragment_key.trim() || `consultant.content_${Date.now()}`
      await saveReportCaseFragment(this.reportCase.id, step.step_key, fragmentKey, {
        expected_revision_no: null,
        fragment_type: 'ANALYSIS',
        title: draft.title.trim() || null,
        content: draft.content.trim(),
        status: 'PROPOSED',
        finding_refs: splitReferences(draft.finding_refs),
        fragment_refs: [],
        evidence_refs: splitReferences(draft.evidence_refs),
        edit_kind: 'SEMANTIC'
      })
      this.newReportFragment = { fragment_key: '', title: '', content: '', finding_refs: '', evidence_refs: '' }
      await this.loadReportCaseData(this.reportCase.id)
      this.message = '新增的报告内容已加入待确认列表。'
    } catch (error) {
      this.message = error.response?.status === 409
        ? '这段报告内容已存在，列表已刷新。'
        : this.errorText(error)
      if (error.response?.status === 409) await this.loadReportCaseData(this.reportCase.id)
    } finally {
      this.reportFragmentSaving = false
    }
  }
}
