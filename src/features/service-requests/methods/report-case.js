import {
  completeReportCaseStep,
  confirmReportCaseNarrativePlan,
  generateReportCaseFragment,
  generateReportNarrativeCandidates,
  getReportCase,
  getReportCaseContent,
  getReportCaseNarrative,
  reopenReportCaseStep,
  returnReportCaseStep,
  saveReportCaseFinding,
  saveReportCaseFragment,
  startReportCaseStep
} from '../../report-cases/api.js'

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
      const [reportCase, content, narrative] = await Promise.all([
        getReportCase(caseId),
        getReportCaseContent(caseId),
        getReportCaseNarrative(caseId)
      ])
      this.reportCase = reportCase
      this.reportCaseContent = content
      this.reportNarrative = narrative
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
              core_theme: candidate.theme || '',
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
      ...(this.reportNarrative.fragment_runs || [])
    ]
    if (!runs.some(run => ['PENDING', 'RUNNING'].includes(run.status))) return
    this.reportNarrativePollTimer = setTimeout(async () => {
      if (this.reportCase?.id !== caseId) return
      try {
        const [content, narrative] = await Promise.all([
          getReportCaseContent(caseId),
          getReportCaseNarrative(caseId)
        ])
        this.reportCaseContent = content
        this.reportNarrative = narrative
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
                core_theme: candidate.theme || '',
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
  async generateNarrativeCandidates() {
    const step = this.currentReportStep
    if (!this.reportCase || !step || step.status !== 'IN_REVIEW' || this.reportNarrativeSaving) return
    this.reportNarrativeSaving = true
    try {
      await generateReportNarrativeCandidates(this.reportCase.id, step.step_key, {
        idempotency_key: `case-${this.reportCase.id}-narrative-${Date.now()}`
      })
      await this.loadReportCaseData(this.reportCase.id)
      this.message = '叙事候选已加入运行队列。'
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.reportNarrativeSaving = false
    }
  },
  async confirmNarrativeCandidate(run, candidate) {
    const draft = this.narrativeCandidateDrafts[this.narrativeDraftKey(run, candidate)] || {}
    if (!this.reportCase || this.reportNarrativeSaving) return
    const confirmed = await this.confirmAction({
      title: '确认叙事方案',
      message: `将“${draft.core_theme || candidate.theme}”确认为第 ${Number(this.reportNarrative.current_plan?.version_no || 0) + 1} 版 NarrativePlan？`,
      confirmButtonText: '确认方案'
    })
    if (!confirmed) return
    this.reportNarrativeSaving = true
    try {
      await confirmReportCaseNarrativePlan(this.reportCase.id, {
        skill_run_id: run.id,
        candidate_key: candidate.candidate_key,
        overrides: {
          core_theme: draft.core_theme || candidate.theme,
          must_include_findings: draft.must_include_findings || candidate.supporting_findings || [],
          self_direction: draft.self_direction || null
        }
      })
      await this.loadReportCaseData(this.reportCase.id)
      this.message = 'NarrativePlan 已确认并保存为新版本。'
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
      this.message = '报告片段已加入写作队列。'
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
      this.message = '当前步骤已开始，可以审核 Case 内容。'
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
      this.message = `${step.step_key} 已重新打开。`
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
      this.message = 'Finding 新版本已保存。'
    } catch (error) {
      this.message = error.response?.status === 409
        ? 'Finding 已被其他人更新，内容已刷新，请确认后再编辑。'
        : this.errorText(error)
      if (error.response?.status === 409) await this.loadReportCaseData(this.reportCase.id)
    } finally {
      this.reportFindingSaving = false
    }
  },
  async addReportFinding() {
    const draft = this.newReportFinding
    const step = this.currentReportStep
    if (!this.reportCase || !step || !draft.finding_key.trim() || !draft.claim.trim() || this.reportFindingSaving) return
    this.reportFindingSaving = true
    try {
      await saveReportCaseFinding(this.reportCase.id, step.step_key, draft.finding_key.trim(), {
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
      this.newReportFinding = { finding_key: '', claim: '', semantic_role: '', evidence_refs: '' }
      await this.loadReportCaseData(this.reportCase.id)
      this.message = '新 Finding 已加入待审核列表。'
    } catch (error) {
      this.message = error.response?.status === 409
        ? '该 Finding 标识已存在，列表已刷新。'
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
      this.message = 'Fragment 新版本已保存。'
    } catch (error) {
      this.message = error.response?.status === 409
        ? 'Fragment 已被其他人更新，内容已刷新，请确认后再编辑。'
        : this.errorText(error)
      if (error.response?.status === 409) await this.loadReportCaseData(this.reportCase.id)
    } finally {
      this.reportFragmentSaving = false
    }
  },
  async addReportFragment() {
    const draft = this.newReportFragment
    const step = this.currentReportStep
    if (!this.reportCase || !step || !draft.fragment_key.trim() || !draft.content.trim() || this.reportFragmentSaving) return
    this.reportFragmentSaving = true
    try {
      await saveReportCaseFragment(this.reportCase.id, step.step_key, draft.fragment_key.trim(), {
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
      this.message = '新 Fragment 已加入。'
    } catch (error) {
      this.message = error.response?.status === 409
        ? '该 Fragment 标识已存在，列表已刷新。'
        : this.errorText(error)
      if (error.response?.status === 409) await this.loadReportCaseData(this.reportCase.id)
    } finally {
      this.reportFragmentSaving = false
    }
  }
}
