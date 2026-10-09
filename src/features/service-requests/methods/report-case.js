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
  getNodeReview,
  importReportCaseContent,
  patchNodeReview,
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
import { canHandleStep } from '../../report-cases/professional-ownership.js'
import { reportFragmentTitle } from '../../report-cases/stages.js'
import {
  SIMPLE_REPORT_WORKFLOW_KEY,
  reportWorkflowKeyFromSources
} from '../../report-cases/workflow-keys.js'

function splitReferences(value) {
  return String(value || '')
    .split(/[\n,，]/)
    .map(item => item.trim())
    .filter(Boolean)
}

function usesAggregateAnalysisReview(reportCase, stepKey) {
  return reportCase?.review_policy_version === 'six-node-review-v1'
    && ['S1', 'S2', 'S3', 'S4'].includes(stepKey)
}

const IMPORT_AUTHORING_STEP_KEYS = ['S1', 'S2', 'S3', 'S4', 'S5']
const IMPORTABLE_STEP_STATUSES = ['PENDING', 'READY']
const REPORT_IMPORT_CONTENT_LIMIT = 100000

function reportImportErrorText(error, fallback) {
  const detail = error.response?.data?.detail
  const code = typeof detail === 'string' ? detail : ''
  const messages = {
    report_import_content_required: '请粘贴或上传报告正文后再导入。',
    report_import_content_too_long: `报告正文超过 ${REPORT_IMPORT_CONTENT_LIMIT} 字上限，请拆分后再导入。`,
    report_import_format_invalid: '报告结构无法识别，请检查正文后重试。',
    report_import_sections_missing: '报告缺少必要段落，系统也未能自动整理，请检查正文后重试。',
    report_import_duplicate_section: '报告中有重复的段落标题，系统也未能自动整理，请检查正文后重试。',
    report_import_section_empty: '有段落内容为空，系统也未能自动整理，请补全正文后再试。',
    report_import_section_too_long: '有段落内容过长，请精简后再导入。',
    report_import_normalization_failed: '系统暂时无法整理报告结构，请检查正文后重试。',
    report_import_content_sha256_invalid: '报告校验值生成失败，请重新选择文件后重试。',
    report_import_content_sha256_mismatch: '报告内容在提交前发生了变化，请确认正文后重新导入。',
    report_import_idempotency_key_required: '导入标识生成失败，请关闭后重新打开导入窗口。',
    report_import_idempotency_conflict: '这次导入与已有记录不一致。请刷新报告后重新打开导入窗口。',
    report_import_duplicate_content: '同一份报告已被导入到另一份申请，请确认是否选错了申请。',
    report_import_case_not_importable: '这份申请已进入其他流程，无法再走快速导入。请刷新后查看当前节点。',
    report_case_forbidden: '当前专业或负责人没有导入这份报告的权限。',
    report_case_not_found: '未找到这份报告申请，请返回列表刷新后重试。'
  }
  return messages[code] || fallback
}

async function sha256Hex(content) {
  if (!globalThis.crypto?.subtle) throw new Error('report_import_content_sha256_invalid')
  const digest = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(content))
  return Array.from(new Uint8Array(digest)).map(byte => byte.toString(16).padStart(2, '0')).join('')
}

function newImportIdempotencyKey() {
  return globalThis.crypto?.randomUUID
    ? globalThis.crypto.randomUUID()
    : `report-import-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export default {
  async continueWholeNodeReview() {
    await this.loadReportCaseData(this.reportCase.id, { silent: true })
    const active = this.reportCase.workflow_instance?.steps.find(step => ['READY', 'IN_REVIEW', 'EXECUTING', 'WAITING_REVIEW'].includes(step.status))
    if (active) this.selectReportNode(active.step_key)
    else { this.selectedReportStepKey = ''; this.workspaceSection = 'overview'; await this.loadWorkspace?.(this.selectedRequest?.id) }
  },
  async loadReportCaseData(caseId, { silent = false } = {}) {
    if (!silent) this.reportCaseLoading = true
    if (this.reportCase?.id !== Number(caseId)) {
      this.narrativeFeedbackDrafts = {}
      this.qualityFeedbackDraft = ''
      this.foundationError = ''
    }
    if (this.reportNarrativePollTimer) {
      clearTimeout(this.reportNarrativePollTimer)
      this.reportNarrativePollTimer = null
    }
    try {
      const reportCase = await getReportCase(caseId)
      this.reportCase = reportCase
      const workflowKey = reportWorkflowKeyFromSources(
        reportCase,
        this.workspace?.request,
        this.selectedRequest
      )
      if (workflowKey === SIMPLE_REPORT_WORKFLOW_KEY) {
        // The simplified workflow owns its own state: it never reads or polls
        // the production content, narrative, quality or skill-run resources.
        if (this.restoreSimpleReportNode && !this.selectedReportStepKey) this.restoreSimpleReportNode()
        await this.loadSimpleReportCaseData(caseId)
        return
      }
      const [content, narrative, quality, analysisRuns] = await Promise.all([
        getReportCaseContent(caseId),
        getReportCaseNarrative(caseId),
        getReportCaseQuality(caseId),
        getCaseSkillRuns(caseId)
      ])
      if (this.restoreReportNode && !this.selectedReportStepKey) this.restoreReportNode()
      this.reportCaseContent = content
      this.reportNarrative = narrative
      this.reportQuality = quality
      this.reportAnalysisRuns = analysisRuns
      const activeStep = (reportCase.workflow_instance?.steps || []).find(step =>
        ['READY', 'IN_REVIEW', 'EXECUTING', 'WAITING_REVIEW'].includes(step.status)
      )
      this.reportCaseCompletionGate = !reportCase.review_policy_version && activeStep?.status === 'IN_REVIEW' && canHandleStep(activeStep, this.staffActor)
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
          title: reportFragmentTitle(fragment.fragment_key, fragment.title || ''),
          content: fragment.content,
          status: fragment.status === 'STALE' ? 'PROPOSED' : fragment.status,
          fragment_type: fragment.fragment_type,
          edit_kind: fragment.status === 'STALE' || usesAggregateAnalysisReview(reportCase, this.selectedReportStepKey) ? 'SEMANTIC' : 'STYLE',
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
      this.resumeGeneratedReportReview?.()
      this.scheduleNarrativePoll(caseId)
    } catch (error) {
      this.message = this.errorText(error)
      throw error
    } finally {
      if (!silent) this.reportCaseLoading = false
    }
  },
  narrativeDraftKey(run, candidate) {
    return `${run.id}:${candidate.candidate_key}`
  },
  scheduleNarrativePoll(caseId) {
    if (reportWorkflowKeyFromSources(this.reportCase, this.workspace?.request, this.selectedRequest) === SIMPLE_REPORT_WORKFLOW_KEY) {
      return
    }
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
        this.reportCaseCompletionGate = activeStep?.status === 'IN_REVIEW' && canHandleStep(activeStep, this.staffActor)
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
            title: reportFragmentTitle(fragment.fragment_key, fragment.title || ''),
            content: fragment.content,
            status: fragment.status === 'STALE' ? 'PROPOSED' : fragment.status,
            fragment_type: fragment.fragment_type,
            edit_kind: fragment.status === 'STALE' || usesAggregateAnalysisReview(this.reportCase, this.selectedReportStepKey) ? 'SEMANTIC' : 'STYLE',
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
        this.resumeGeneratedReportReview?.()
        this.scheduleNarrativePoll(caseId)
      } catch (error) {
        this.message = this.errorText(error)
      }
    }, 1800)
  },
  async runReportQuality(feedbackRequest = null) {
    if (!this.reportCase || this.reportQualitySaving) return
    const feedback = String(feedbackRequest?.runtimeInstruction || '').trim()
    const sourceRunId = Number(feedbackRequest?.sourceRunId) || null
    if (feedback.length > 4000) {
      this.message = '反馈不能超过 4000 个字符。'
      return
    }
    if (feedback && !sourceRunId) {
      this.message = '请选择一条已完成的检查结果，再提交反馈。'
      return
    }
    this.reportQualitySaving = true
    this.finalGateNote = ''
    try {
      this.reportQuality = await runReportCaseQuality(this.reportCase.id, {
        idempotency_key: `case-${this.reportCase.id}-qa-${Date.now()}`,
        runtime_instruction: feedback || null,
        source_run_id: feedback ? sourceRunId : null
      })
      if (
        feedback
        && this.reportQuality.quality_status !== 'PROGRAMMATIC_BLOCKED'
        && this.reportQuality.latest_validator_run?.id !== sourceRunId
      ) this.qualityFeedbackDraft = ''
      this.scheduleNarrativePoll(this.reportCase.id)
      const advisoryOnly = this.reportCase.review_policy_version === 'import-review-v1' || this.reportQuality.advisory_only
      const blocked = this.reportQuality.quality_status === 'PROGRAMMATIC_BLOCKED'
      if (blocked) {
        this.message = advisoryOnly
          ? '交付前检查发现需要人工确认的内容；这些只是建议，不阻断交付，请核对后完成最终确认。'
          : '交付前检查发现必须处理的问题，请先修订报告内容。'
      } else if (feedback) {
        this.message = '已收到检查反馈，正在依据完整报告重新复核。'
      } else {
        this.message = advisoryOnly
          ? '交付前检查已开始；结果作为复核建议，不阻断交付。'
          : '交付前检查已开始。'
      }
    } catch (error) {
      this.message = this.errorText(error)
    } finally {
      this.reportQualitySaving = false
    }
  },
  async rerunReportQualityWithFeedback() {
    const run = this.reportQuality.latest_validator_run
    if (!run || run.status !== 'COMPLETED' || !run.current) return
    await this.runReportQuality({
      runtimeInstruction: this.qualityFeedbackDraft,
      sourceRunId: run.id
    })
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
    if (!this.reportCase || this.reportStepSaving) return
    // 交付快照只组装已确认的段落；修订稿未整体确认时先引导咨询师回看。
    const pendingManuscript = (this.reportCaseContent?.fragments || [])
      .filter(item => item.fragment_type === 'REPORT' && item.status === 'PROPOSED')
    if (pendingManuscript.length) {
      this.message = `还有 ${pendingManuscript.length} 段修订尚未确认，请先在“修改后稿件”通读并确认最终稿。`
      return
    }
    const staleManuscript = (this.reportCaseContent?.fragments || [])
      .filter(item => item.fragment_type === 'REPORT' && item.status === 'STALE')
    if (staleManuscript.length) {
      this.message = `有 ${staleManuscript.length} 段正文的来源依据已更新，交付版本不会包含这些段落；请先在“修改后稿件”复核来源并确认最终稿。`
      return
    }
    const advisoryCount = this.reportQuality.advisory_only ? (this.reportQuality.unresolved_advisories?.length || 0) : 0
    const confirmed = await this.confirmAction({
      title: '确认最终复核',
      message: advisoryCount
        ? `AI 检查还有 ${advisoryCount} 条未处理建议，这些建议不会阻断交付。确认完成最终复核并承担交付责任？`
        : '确认完成最终复核并承担交付责任？',
      confirmButtonText: '确认并完成'
    })
    if (!confirmed) return
    this.reportStepSaving = true
    try {
      await approveReportCaseFinalGate(this.reportCase.id, {
        attested: true,
        note: (this.finalGateNote || '').trim() || null
      })
      this.finalGateNote = ''
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
  async rerunNarrativeWithFeedback(run) {
    const step = this.currentReportStep
    const feedback = String(this.narrativeFeedbackDrafts[run?.id] || '').trim()
    if (!this.reportCase || !step || step.step_key !== 'S5' || step.status !== 'IN_REVIEW' || this.reportNarrativeSaving) return
    if (!run || run.status !== 'COMPLETED' || !feedback) return
    if (feedback.length > 4000) {
      this.message = '反馈不能超过 4000 个字符。'
      return
    }
    this.reportNarrativeSaving = true
    try {
      await generateReportNarrativeCandidates(this.reportCase.id, step.step_key, {
        idempotency_key: `case-${this.reportCase.id}-narrative-feedback-${run.id}-${Date.now()}`,
        runtime_instruction: feedback,
        source_run_id: run.id
      })
      this.narrativeFeedbackDrafts[run.id] = ''
      await this.loadReportCaseData(this.reportCase.id)
      this.message = '已收到主线建议反馈，正在生成新的 AI 候选；旧结果仍保留用于对照。'
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
      await this.loadReportCaseData(this.reportCase.id, { silent: true })
      this.nodeWritingMode = 'allocation'
      this.scrollWorkspaceToTop()
      this.message = '报告主线已确认，已进入逐段编排。核对内容安排后可按顺序生成正文。'
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
      this.reportReviewAutoOpen = true
      this.nodeWritingMode = 'progress'
      await this.loadReportCaseData(this.reportCase.id, { silent: true })
      this.message = '报告内容已开始按顺序生成；检查完成后请通读全文并整体审阅。'
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
      await this.loadReportCaseData(this.reportCase.id, { silent: true })
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
  async rerunReportFragmentWithFeedback(run) {
    const step = this.currentReportStep
    const feedback = String(this.narrativeFeedbackDrafts[run?.id] || '').trim()
    if (!this.reportCase || !step || step.step_key !== 'S5' || step.status !== 'IN_REVIEW' || this.reportNarrativeSaving) return
    if (!run || run.status !== 'COMPLETED' || !run.target_key || !feedback) return
    if (feedback.length > 4000) {
      this.message = '反馈不能超过 4000 个字符。'
      return
    }
    this.reportNarrativeSaving = true
    try {
      await generateReportCaseFragment(this.reportCase.id, step.step_key, {
        idempotency_key: `case-${this.reportCase.id}-fragment-feedback-${run.id}-${Date.now()}`,
        fragment_key: run.target_key,
        runtime_instruction: feedback,
        source_run_id: run.id
      })
      this.narrativeFeedbackDrafts[run.id] = ''
      await this.loadReportCaseData(this.reportCase.id)
      this.message = '已收到本段写作反馈，新版本正在生成并会进入人工审核。'
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
      await this.loadReportCaseData(this.reportCase.id, { silent: true })
      this.setReportWorkspaceSection('upstream')
      this.message = `已开始${this.reportStepLabel(step.step_key)}，请先核对上游输入，再继续本节点工作。`
    } catch (error) {
      // 节点可能已由上游成果就绪事件自动开始；先把最新状态取回来再提示。
      try {
        await this.loadReportCaseData(this.reportCase.id, { silent: true })
      } catch (refreshError) {
        // 保留原始失败信息。
      }
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
      message: '确认已完成当前节点的人工审核？完成后将打开下一节点，同专业负责人可继续开始处理，跨专业节点交给对应负责人。',
      confirmButtonText: '完成并进入下一节点'
    })
    if (!confirmed) return
    this.reportStepSaving = true
    try {
      await completeReportCaseStep(this.reportCase.id, step.step_key, {
        reviewed_finding_count: this.reportCaseContent.findings.length,
        reviewed_fragment_count: this.reportCaseContent.fragments.length
      })
      await this.loadReportCaseData(this.reportCase.id, { silent: true })
      this.showNextReportStep(step)
    } catch (error) {
      this.message = error.response?.data?.detail === 'report_authoring_not_ready'
        ? '写作节点还有待办：请逐段确认正文，并重新检查修改后的报告连贯性。'
        : this.errorText(error)
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
      // API values are JSON; serialization also detaches nested reactive proxies.
      relation_refs: JSON.parse(JSON.stringify(finding.relation_refs || [])),
      structured_data: JSON.parse(JSON.stringify(finding.structured_data_json || {})),
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
      const status = ['S1', 'S2', 'S3', 'S4'].includes(step.step_key) ? 'PROPOSED' : draft.status
      const editKind = fragment.status === status ? draft.edit_kind : 'SEMANTIC'
      if (usesAggregateAnalysisReview(this.reportCase, step.step_key) && editKind === 'SEMANTIC') {
        const review = await getNodeReview(this.reportCase.id, step.step_key)
        const current = review.snapshot.fragments.find(item => item.fragment_key === fragment.fragment_key)
        if (!current || current.revision_no !== fragment.revision_no) {
          const conflict = new Error('fragment_revision_conflict')
          conflict.response = { status: 409 }
          throw conflict
        }
        await patchNodeReview(this.reportCase.id, step.step_key, {
          fingerprint: review.fingerprint,
          changes: [{
            kind: 'fragment',
            key: fragment.fragment_key,
            title: String(draft.title || '').trim(),
            content: draft.content
          }]
        })
      } else {
        await saveReportCaseFragment(this.reportCase.id, step.step_key, fragment.fragment_key, {
          expected_revision_no: fragment.revision_no,
          fragment_type: draft.fragment_type,
          title: draft.title,
          content: draft.content,
          status,
          finding_refs: splitReferences(draft.finding_refs),
          fragment_refs: splitReferences(draft.fragment_refs),
          evidence_refs: splitReferences(draft.evidence_refs),
          edit_kind: editKind
        })
      }
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
  },
  canImportReportCase(reportCase = this.reportCase) {
    if (!reportCase || ['DELIVERED', 'CANCELLED'].includes(reportCase.status)) return false
    if (reportCase.review_policy_version !== 'six-node-review-v1') return false
    const steps = reportCase.workflow_instance?.steps || []
    const byKey = Object.fromEntries(steps.map(step => [step.step_key, step]))
    return IMPORT_AUTHORING_STEP_KEYS.every(key =>
      IMPORTABLE_STEP_STATUSES.includes(byKey[key]?.status)
    ) && Boolean(byKey.S6)
  },
  openReportImport() {
    if (!this.canImportReportCase() || this.reportImportDialog.saving) return
    this.reportImportDialog = {
      visible: true,
      title: '',
      sourceFilename: '',
      content: '',
      error: '',
      saving: false,
      idempotencyKey: newImportIdempotencyKey()
    }
  },
  async handleReportImportFile(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    if (file.size > REPORT_IMPORT_CONTENT_LIMIT * 4) {
      this.reportImportDialog.error = '文件过大，请确认这是一份完整报告正文。'
      return
    }
    try {
      this.reportImportDialog.content = await file.text()
      this.reportImportDialog.sourceFilename = file.name.slice(0, 240)
      this.reportImportDialog.error = ''
    } catch {
      this.reportImportDialog.error = '无法读取这份文件，请改用粘贴或换一个文本文件。'
    }
  },
  async submitReportImport() {
    const dialog = this.reportImportDialog
    const content = dialog.content.trim()
    if (!content) { dialog.error = '请粘贴或上传报告正文。'; return }
    if (content.length > REPORT_IMPORT_CONTENT_LIMIT) {
      dialog.error = `报告正文超过 ${REPORT_IMPORT_CONTENT_LIMIT} 字上限，请拆分后再导入。`
      return
    }
    if (dialog.saving || !this.reportCase) return
    dialog.saving = true
    dialog.error = ''
    try {
      const contentSha256 = await sha256Hex(content)
      await importReportCaseContent(this.reportCase.id, {
        title: dialog.title.trim() || null,
        content,
        source_filename: dialog.sourceFilename.trim() || null,
        content_sha256: contentSha256,
        idempotency_key: dialog.idempotencyKey
      })
      const caseId = this.reportCase.id
      dialog.visible = false
      await this.loadReportCaseData(caseId)
      this.selectReportNode('S6')
      this.message = '报告已导入，前五个节点标记为已完成。请在第 6 步运行一次 AI 检查作为参考，然后完成最终确认并交付。'
    } catch (error) {
      dialog.idempotencyKey = newImportIdempotencyKey()
      dialog.error = reportImportErrorText(error, this.errorText(error))
    } finally {
      dialog.saving = false
    }
  }
}
