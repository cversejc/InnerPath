import { authState, hasRole } from '../stores/auth'
import { Button as VanButton, Dialog as VanDialog, Field as VanField } from 'vant'
import {
  SERVICE_REQUEST_STATUS_LABELS,
  birthSummary as formatBirthSummary,
  consultationTypeLabel,
  errorText,
  formatDate,
  genderLabel,
  prettyJson,
  requestGoal,
  topicLabel
} from '../features/service-requests/formatters.js'
import {
  calendarEditorFromPayload,
  reportEditorFromPayload
} from '../features/service-requests/payloads.js'
import { canHandleStep, canAcceptRequest, ownsRequest, specialtyLabels, consultantCanHandle } from '../features/report-cases/professional-ownership.js'
import assignmentMethods from '../features/service-requests/methods/assignment.js'
import queueMethods from '../features/service-requests/methods/queue.js'
import workflowMethods from '../features/service-requests/methods/workflow.js'
import reportCaseMethods from '../features/service-requests/methods/report-case.js'
import reportAnalysisMethods from '../features/service-requests/methods/report-analysis.js'
import reportFoundationMethods from '../features/service-requests/methods/report-foundation.js'
import reportReviewMethods from '../features/service-requests/methods/report-review.js'
import ReportNodeWorkbench from '../features/report-cases/components/ReportNodeWorkbench.vue'
import AnalysisDraftsPanel from '../features/report-cases/components/AnalysisDraftsPanel.vue'
import FoundationCalculationPanel from '../features/report-cases/components/FoundationCalculationPanel.vue'
import WorkbenchRecordPicker from '../features/report-cases/components/WorkbenchRecordPicker.vue'
import QualityScorecard from '../features/report-cases/components/QualityScorecard.vue'
import ReportFragmentReview from '../features/report-cases/components/ReportFragmentReview.vue'
import QualityIssueReview from '../features/report-cases/components/QualityIssueReview.vue'
import EvidenceReferencePicker from '../features/report-cases/components/EvidenceReferencePicker.vue'
import { nodeWorkspaceComputed, nodeWorkspaceMethods } from '../features/report-cases/node-workspace-state.js'
import DeliveredReportSummary from '../features/report-cases/components/DeliveredReportSummary.vue'
import { REPORT_STEP_STATUS_LABELS, reportFragmentTitle, reportStage } from '../features/report-cases/stages.js'
import {
  buildApplicationContextItems,
  buildApplicationProfileItems,
  formatConsultantEvidenceValue,
  reportEvidenceTitle,
  visibleConsultantEvidence
} from '../features/report-cases/workbench-inputs.js'
import { confirmAction } from '../utils/confirmAction.js'

export default {
  name: 'StaffConsole',
  components: { VanButton, VanDialog, VanField, ReportNodeWorkbench, AnalysisDraftsPanel, FoundationCalculationPanel, DeliveredReportSummary, WorkbenchRecordPicker, QualityScorecard, ReportFragmentReview, QualityIssueReview, EvidenceReferencePicker },
  data() {
    const admin = hasRole('admin')
    return {
      admin,
      scope: admin ? 'all' : 'mine',
      scopeOptions: admin
        ? [{ id: 'all', label: '全部申请' }, { id: 'available', label: '待接单' }, { id: 'mine', label: '我的报告' }]
        : [{ id: 'mine', label: '我的报告' }, { id: 'available', label: '待接单' }],
      serviceType: 'report',
      statusFilter: '',
      statusOptions: ['submitted', 'accepted', 'ai_processing', 'ai_ready', 'reviewing', 'needs_info', 'failed', 'delivered'],
      requests: { total: 0, items: [] },
      selectedRequest: null,
      workspaceSection: 'overview',
      selectedReportStepKey: '',
      nodeRecordKeys: {findings:'',fragments:'',quality:'',planned:'',candidate:''},
      nodeWritingMode: 'plan',
      showNodeAddForm: false,
      workspace: null,
      reportCase: null,
      reportCaseContent: { evidence: [], findings: [], fragments: [] },
      reportCaseCompletionGate: null,
      reportAnalysisRuns: [],
      reportNarrative: { current_plan: null, candidate_runs: [], fragment_runs: [] },
      reportQuality: {
        quality_status: 'NOT_RUN',
        latest_validator_run: null,
        issues: [],
        can_approve: false,
        blocking_count: 0,
        open_count: 0
      },
      reportQualityIssueDrafts: {},
      qualityFeedbackDraft: '',
      reportQualitySaving: false,
      reportCaseDelivering: false,
      finalGateAttested: false,
      reportCaseLoading: false,
      reportAnalysisSaving: false,
      reportAnalysisFindingSavingKey: '',
      reportAnalysisFragmentSavingKey: '',
      foundationSaving: false,
      foundationError: '',
      reportNarrativeSaving: false,
      reportNarrativePollTimer: null,
      narrativeCandidateDrafts: {},
      narrativeFeedbackDrafts: {},
      newReportWritingFragment: { fragment_key: '', title: '' },
      reportStepSaving: false,
      reportStepReturn: { visible: false, targetStepKey: '', reason: '' },
      editingFindingKey: null,
      reportFindingDraft: null,
      newReportFinding: { finding_key: '', claim: '', semantic_role: 'OBSERVATION', evidence_refs: '' },
      reportFindingSaving: false,
      reportFragmentDrafts: {},
      newReportFragment: { fragment_key: '', title: '', content: '', finding_refs: '', evidence_refs: '' },
      reportFragmentSaving: false,
      reportReviewBusy: false,
      reportReviewAutoOpen: false,
      loading: false,
      accepting: false,
      aiStarting: false,
      saving: false,
      delivering: false,
      infoSaving: false,
      pollingTask: false,
      task: null,
      pollTimer: null,
      message: '',
      showInfoPanel: false,
      infoReason: '',
      infoStepKey: '',
      rejectDialog: { visible: false, reason: '', error: '' },
      rejectSaving: false,
      reportEditor: reportEditorFromPayload(),
      calendarEditor: calendarEditorFromPayload(),
      consultants: [],
      assignmentId: null,
      consultationType: 'integrated',
      assignmentSaving: false
    }
  },
  computed: {
    staffActor() { return authState.user },
    canAcceptSelectedRequest() { return canAcceptRequest(this.selectedRequest, this.staffActor) },
    ownsSelectedRequest() { return ownsRequest(this.selectedRequest, this.staffActor) },
    specialtyLabel() { return specialtyLabels[this.staffActor?.consultant_type] || (this.admin ? "管理员" : "尚未设置专业类型") },
    ...nodeWorkspaceComputed,
    currentReportStep() {
      const steps = this.reportCase?.workflow_instance?.steps || []
      return steps.find(step => ['READY', 'IN_REVIEW', 'EXECUTING', 'WAITING_REVIEW'].includes(step.status)) || null
    },
    latestReportAnalysisRun() {
      if (!this.currentReportStep) return null
      return this.reportAnalysisRuns
        .filter(run => run.target_type === 'REPORT_ANALYSIS_DRAFT' && run.target_key === this.currentReportStep.step_key)
        .sort((left, right) => right.id - left.id)[0] || null
    },
    reportAnalysisPending() {
      return this.reportAnalysisSaving || this.reportAnalysisRuns.some(run => ['PENDING', 'RUNNING'].includes(run.status))
    },
    reportReturnTargets() {
      const active = this.currentReportStep
      if (!active) return []
      return (this.reportCase?.workflow_instance?.steps || []).filter(step =>
        step.sequence_no < active.sequence_no && step.status === 'COMPLETED'
      )
    },
    scopeDescription() {
      if (this.scope === 'available') return `展示尚缺${this.specialtyLabel}的报告申请，接单后负责对应节点。`
      if (this.scope === 'mine') return '展示分配给当前咨询师的申请。'
      return '管理员可查看全量申请并介入处理。'
    },
    birthSummary() {
      return formatBirthSummary(this.workspace)
    },
    assignableConsultants() {
      if (this.workspace?.request.service_type !== 'report') return this.consultants
      const required = this.consultationType === 'integrated'
        ? ['mingli', 'psychology']
        : [this.consultationType === 'metaphysics' ? 'mingli' : 'psychology']
      return this.consultants.filter(consultant => required.every(
        specialty => consultantCanHandle(consultant, specialty)
      ))
    },
    assignmentChanged() {
      if (!this.workspace) return false
      const request = this.workspace.request
      return Number(this.assignmentId || 0) !== Number(request.assigned_consultant_id || 0) || (
        request.service_type === 'report' && this.consultationType !== (request.consultation_type || 'integrated')
      )
    },
    reportContentPlan() {
      return this.reportNarrative.current_plan?.plan_json?.content_plan || null
    },
    reportProfileItems() {
      return buildApplicationProfileItems(this.reportCase?.application_snapshot)
    },
    reportContextItems() {
      return buildApplicationContextItems(this.reportCase?.application_snapshot)
    },
    reportEvidenceItems() {
      return this.reportCaseContent.evidence || []
    },
    reportReferenceFindings() {
      const step = this.selectedReportStep
      const steps = this.reportCase?.workflow_instance?.steps || []
      const allowedStepIds = new Set(steps
        .filter(item => step && item.sequence_no <= step.sequence_no)
        .map(item => item.id))
      return (this.reportCaseContent.findings || []).filter(item => item.status === 'CONFIRMED'
        && (!item.owner_step_task_id || allowedStepIds.has(item.owner_step_task_id)))
    },
    reportPreferredEvidenceKeys() {
      const stepKey = this.selectedReportStepKey
      const activeEvidence = visibleConsultantEvidence(this.reportEvidenceItems).filter(item => item.status === 'ACTIVE')
      const refs = this.reportReferenceFindings.flatMap(item => item.evidence_refs || [])
      const userContextKeys = activeEvidence
        .filter(item => ['USER_PROVIDED', 'USER_CONTEXT', 'APPLICATION_CONTEXT'].includes(item.source_type)
          || item.evidence_key?.startsWith('input.context.')
          || item.evidence_key === 'input.additional_info')
        .map(item => item.evidence_key)
      if (stepKey === 'S1') {
        return activeEvidence
          .filter(item => ['SYSTEM_CALCULATED', 'CONSULTANT_CORRECTED'].includes(item.source_type)
            || /^input\.profile\.(birth_|calendar_type$|time_accuracy$|birth_is_leap_month$)/.test(item.evidence_key || ''))
          .map(item => item.evidence_key)
      }
      if (['S2', 'S4'].includes(stepKey)) {
        refs.push(...userContextKeys)
      }
      return [...new Set(refs)]
    },
    reportGeneration() {
      return this.reportNarrative.current_plan?.plan_json?.generation || {}
    },
    reportChapterChecks() {
      const chapters = [...new Set(
        (this.reportContentPlan?.fragments || []).map(item => item.chapter).filter(Boolean)
      )]
      const checks = this.reportGeneration.chapter_checks || {}
      return chapters.map(chapterKey => ({
        chapterKey,
        status: checks[chapterKey]?.status || '待检查'
      }))
    },
    semanticRoleOptions() {
      return [
        { value: 'OBSERVATION', label: '综合观察' },
        { value: 'STRENGTH', label: '优势' },
        { value: 'CHALLENGE', label: '需要留意' },
        { value: 'CONFLICT', label: '内在张力' },
        { value: 'PATTERN', label: '行为模式' },
        { value: 'SIGNAL', label: '待验证线索' },
        { value: 'THEME', label: '核心主题' },
        { value: 'ACTION', label: '行动方向' }
      ]
    },
    narrativePlanStatusLabel() {
      return this.assetStatusLabel(this.reportNarrative.current_plan?.status) || '尚未确定'
    },
    reportGenerationStatusLabel() {
      return {
        NOT_STARTED: '报告内容尚未生成',
        IN_PROGRESS: '正在生成报告内容',
        CHAPTER_COHERENCE_CHECK: '正在检查章节内容',
        COHERENCE_CHECK: '正在检查全文连贯性',
        READY_FOR_REVIEW: '内容已生成，等待逐段审阅',
        BLOCKED: '当前不能开始写作，请先补充已确认的判断',
        NEEDS_INPUT: '需要补充内容后才能继续',
        FAILED: '内容生成暂时失败，可稍后继续',
        PAUSED: '内容生成已暂停，可继续未完成部分',
        CHAPTER_COHERENCE_BLOCKED: '章节检查发现需要处理的问题',
        CHAPTER_COHERENCE_FAILED: '章节检查暂时失败',
        CHAPTER_COHERENCE_STALE: '章节内容已有更新，需要重新检查',
        COHERENCE_BLOCKED: '全文检查发现需要处理的问题',
        COHERENCE_FAILED: '全文检查暂时失败',
        COHERENCE_STALE: '报告内容已有更新，需要重新检查'
      }[this.reportGeneration.status] || '等待生成报告内容'
    },
    workbenchStatusLabel() {
      const caseStatus = this.reportCase?.status
      if (caseStatus === 'DELIVERED') return '已交付'
      if (caseStatus === 'READY_TO_DELIVER') return '待生成交付版本'
      if (caseStatus === 'BLOCKED') return '需要处理'
      if (caseStatus === 'CANCELLED') return '已关闭'
      if (this.currentReportStep) {
        return `${this.reportStepLabel(this.currentReportStep.step_key)} · ${this.reportStepStatusLabel(this.currentReportStep.status)}`
      }
      return this.statusLabel(this.workspace?.request?.status || this.selectedRequest?.status)
    },
    workbenchStatusClass() {
      if (this.reportCase?.status === 'DELIVERED') return 'staff-status-delivered'
      if (this.reportCase?.status === 'BLOCKED') return 'staff-status-needs_info'
      return ''
    },
    skillStudioLocation() {
      const query = { return_to: this.$route.fullPath }
      if (this.reportCase?.id) query.case_id = String(this.reportCase.id)
      if (this.selectedReportStepKey) query.step = this.selectedReportStepKey
      return { path: '/skills', query }
    }
  },
  watch: {
    '$route.query.request_id'(value) {
      const requestId = Number(value)
      if (!Number.isSafeInteger(requestId) || requestId < 1) {
        if (this.selectedRequest) this.clearReportWorkspaceState()
        return
      }
      if (this.selectedRequest?.id === requestId) return
      const request = this.requests.items.find(item => item.id === requestId)
      if (request) this.selectRequest(request, { updateRoute: false })
      else this.clearReportWorkspaceState()
    },
    '$route.query.step'() {
      if(this.reportCase) this.restoreReportNode()
    },
    '$route.query.section'(sectionId) {
      if (!this.selectedRequest) return
      const normalizedSection = {
        inputs: 'upstream',
        context: 'upstream',
        evidence: this.selectedReportStepKey === 'S1' ? 'calculation' : 'upstream',
        suggestions: 'analysis'
      }[sectionId] || sectionId
      const section = this.reportWorkspaceSections.some(item => item.id === normalizedSection)
        ? normalizedSection
        : 'overview'
      if (section === this.workspaceSection) return
      this.workspaceSection = section
      this.scrollWorkspaceToTop()
    }
  },
  mounted() {
    const routeScope = String(this.$route.query.scope || '')
    if (this.scopeOptions.some(option => option.id === routeScope)) this.scope = routeScope
    this.loadRequests().then(() => this.restoreWorkspaceFromRoute())
    this.loadConsultants()
  },
  beforeUnmount() {
    this.stopPolling()
    if (this.reportNarrativePollTimer) clearTimeout(this.reportNarrativePollTimer)
  },
  methods: {
    canHandleReportStep(step) { return canHandleStep(step, this.staffActor) },
    consultantCanHandle,
    openReportInfoPanel(step) {
      this.infoStepKey = step?.step_key || this.currentReportStep?.step_key || ''
      this.infoReason = ''
      this.showInfoPanel = Boolean(this.infoStepKey)
    },
    confirmAction,
    ...queueMethods,
    ...workflowMethods,
    ...reportCaseMethods,
    ...reportAnalysisMethods,
    ...reportFoundationMethods,
    ...reportReviewMethods,
    ...assignmentMethods,
    ...nodeWorkspaceMethods,
    reportFragmentStatus(fragmentKey) {
      const status = this.reportCaseContent.fragments.find(item => item.fragment_key === fragmentKey)?.status
      return this.assetStatusLabel(status) || '待撰写'
    },
    addEntry() {
      this.calendarEditor.entries.push({
        _key: `new-${Date.now()}-${Math.random()}`,
        entry_date: '',
        tone: 'yellow',
        status_label: '',
        keyword: '',
        summary: '',
        suitableText: '',
        unsuitableText: '',
        time_window: '',
        admin_note: ''
      })
    },
    removeEntry(index) {
      this.calendarEditor.entries.splice(index, 1)
    },
    statusLabel(status) {
      return SERVICE_REQUEST_STATUS_LABELS[status] || '处理中'
    },
    reportStepLabel(stepKey) {
      return reportStage(stepKey)?.shortName || '处理步骤'
    },
    reportStepStatusLabel(status) {
      return REPORT_STEP_STATUS_LABELS[status] || '处理中'
    },
    setReportWorkspaceSection(sectionId) {
      if (this.reportReviewBusy) { this.message = '请先保存或取消当前修改，再切换工作界面。'; return }
      const sectionMap = {
        'case-context': 'upstream',
        'case-evidence': this.selectedReportStepKey === 'S1' ? 'calculation' : 'upstream',
        'case-calculation': 'calculation',
        'case-analysis': 'analysis',
        'case-findings': 'findings',
        'case-fragments': 'fragments',
        'case-narrative': 'writing',
        'case-quality': 'quality'
      }
      const section = sectionMap[sectionId]
        || ({ inputs: 'upstream', suggestions: 'analysis' }[sectionId])
        || sectionId
      if (!this.reportWorkspaceSections.some(item => item.id === section)) return
      this.workspaceSection = section
      if (this.selectedRequest) this.syncWorkspaceRoute(this.selectedRequest.id, section, { history: 'push' })
      this.scrollWorkspaceToTop()
    },
    scrollWorkspaceToTop() {
      this.$nextTick(() => {
        this.$el?.querySelector('.node-workspace-body')?.scrollTo({ top: 0 })
        this.$el?.scrollTo?.({ top: 0 })
        window.scrollTo?.({ top: 0 })
      })
    },
    syncWorkspaceRoute(requestId, section = 'overview', { history = 'replace' } = {}) {
      const query = { ...this.$route.query }
      query.scope = this.scope
      if (requestId) {
        query.request_id = String(requestId)
        query.section = section
        if(this.selectedReportStepKey) query.step = this.selectedReportStepKey
        else query.step = 'all'
      } else {
        delete query.request_id
        delete query.section
        delete query.step
      }
      const currentRequestId = String(this.$route.query.request_id || '')
      const currentSection = String(this.$route.query.section || 'overview')
      const currentScope = String(this.$route.query.scope || '')
      if (
        currentRequestId === String(requestId || '')
        && currentSection === (requestId ? section : 'overview')
        && currentScope === this.scope
        && String(this.$route.query.step || '').replace(/^all$/, '') === (requestId ? this.selectedReportStepKey : '')
      ) return
      return this.$router[history === 'push' ? 'push' : 'replace']({ query })
    },
    async restoreWorkspaceFromRoute() {
      const requestId = Number(this.$route.query.request_id)
      if (!Number.isSafeInteger(requestId) || requestId < 1) return
      const request = this.requests.items.find(item => item.id === requestId)
      if (!request) {
        this.syncWorkspaceRoute(null)
        return
      }
      await this.selectRequest(request, { updateRoute: false })
      this.restoreReportNode()
    },
    closeReportWorkspace() {
      if (this.reportReviewBusy) { this.message = '请先保存或取消当前修改，再关闭报告工作区。'; return }
      this.syncWorkspaceRoute(null)
      this.clearReportWorkspaceState()
    },
    clearReportWorkspaceState() {
      this.stopPolling()
      this.selectedRequest = null
      this.workspace = null
      this.reportCase = null
      this.reportCaseCompletionGate = null
      this.reportReviewBusy = false
      this.reportReviewAutoOpen = false
      this.foundationError = ''
      this.reportCaseContent = { evidence: [], findings: [], fragments: [] }
      this.reportAnalysisRuns = []
      this.reportNarrative = { current_plan: null, candidate_runs: [], fragment_runs: [] }
      this.reportQuality = {
        quality_status: 'NOT_RUN', latest_validator_run: null, issues: [],
        can_approve: false, blocking_count: 0, open_count: 0
      }
      this.qualityFeedbackDraft = ''
      this.narrativeFeedbackDrafts = {}
      this.workspaceSection = 'overview'
      this.selectedReportStepKey = ''
      this.scrollWorkspaceToTop()
    },
    evidenceLabel(evidence) {
      return reportEvidenceTitle(evidence)
    },
    evidenceSourceLabel(sourceType) {
      return {
        SYSTEM_CALCULATED: '系统测算', CONSULTANT_CORRECTED: '咨询师修订', USER_CONTEXT: '申请补充',
        APPLICATION_CONTEXT: '申请补充', USER_PROFILE: '用户档案',
        REPORT: '已交付报告', CONSULTANT: '咨询师补充'
      }[sourceType] || '用户资料'
    },
    evidenceSummary(evidence) {
      const summary = formatConsultantEvidenceValue(evidence.value_json, evidence.source_type)
      return summary === '—' ? '没有补充说明。' : summary
    },
    humanizeReference(value) {
      const labels = {
        birth_profile: '出生资料', birth_date: '出生日期', birth_time: '出生时间',
        four_pillars: '四柱测算', ziwei: '紫微测算', profile: '个人档案', context: '申请情境'
      }
      const parts = String(value || '').split(/[./:_-]+/).filter(Boolean)
      const known = parts.map(part => labels[part]).filter(Boolean)
      return known.join(' · ') || '其他资料来源'
    },
    evidenceTitles(keys) {
      const refs = Array.isArray(keys) ? keys : String(keys || '').split(/[\n,，]/).map(item => item.trim()).filter(Boolean)
      return [...new Set(refs.map(key => {
        const index = this.reportEvidenceItems.findIndex(item => item.evidence_key === key)
        return index >= 0 ? this.evidenceLabel(this.reportEvidenceItems[index]) : ''
      }).filter(Boolean))].join('、')
    },
    findingTitle(key) {
      const finding = this.reportCaseContent.findings.find(item => item.finding_key === key)
      return finding?.claim || '已确认的专业判断'
    },
    findingTitles(keys) {
      const refs = Array.isArray(keys) ? keys : String(keys || '').split(/[\n,，]/).map(item => item.trim()).filter(Boolean)
      return refs.map(key => this.findingTitle(key)).filter(Boolean).join('；')
    },
    fragmentTitle(key, planFragment = null) {
      const fragment = this.reportCaseContent.fragments.find(item => item.fragment_key === key)
      const translated = reportFragmentTitle(key)
      if (translated !== '报告段落') return translated
      const title = planFragment?.title || fragment?.title
      if (title && !/[A-Za-z]{2,}/.test(title)) return title
      if (planFragment?.chapter) return this.chapterLabel(planFragment.chapter)
      const planned = this.reportContentPlan?.fragments?.find(item => item.fragment_key === key)
      return reportFragmentTitle(key, planned?.title || (planned?.chapter ? this.chapterLabel(planned.chapter) : '报告内容'))
    },
    fragmentTitles(keys) {
      const refs = Array.isArray(keys) ? keys : String(keys || '').split(/[\n,，]/).map(item => item.trim()).filter(Boolean)
      return refs.map(key => this.fragmentTitle(key)).join('、')
    },
    chapterLabel(key) {
      const chapter = String(key || '')
      const numbered = chapter.match(/(?:chapter|第)[_ -]?(\d+)/i)
      if (numbered) return `第 ${numbered[1]} 章`
      return ({
        INTRO: '开篇', OVERVIEW: '整体概览', IDENTITY: '第一章 · 心灵结构', BLOCKS: '第二章 · 卡点与机制', CHALLENGE: '第二章 · 卡点与机制', DIRECTION: '第三章 · 方向与成长', ENDING: '寄语', BACKGROUND: '背景', SUMMARY: '总结',
        CONCLUSION: '结语', ACTION_PLAN: '行动建议', CORE_PATTERN: '核心模式'
      })[chapter.toUpperCase()] || '报告章节'
    },
    semanticRoleLabel(role) {
      const option = this.semanticRoleOptions.find(item => item.value === role)
      return option?.label || '综合观察'
    },
    confidenceLabel(value) {
      return { LOW: '较低', MEDIUM: '一般', HIGH: '较高' }[value] || '一般'
    },
    importanceLabel(value) {
      return { LOW: '普通', MEDIUM: '关注', HIGH: '重要', CRITICAL: '优先' }[value] || '普通'
    },
    editKindLabel(value) {
      return { STYLE: '表达调整', SEMANTIC: '内容调整' }[value] || '内容调整'
    },
    assetStatusLabel(status) {
      return {
        ACTIVE: '可用', CONFIRMED: '已确认', PROPOSED: '待审核', REJECTED: '已拒绝',
        STALE: '需要重新审核', OPEN: '待处理', RESOLVED: '已处理', ACCEPTED: '已接受',
        DISMISSED: '已忽略', PENDING: '待开始', RUNNING: '正在处理', COMPLETED: '已完成', FAILED: '暂时失败',
        READY: '待开始', BLOCKED: '需要处理', NOT_RUN: '尚未检查', PASSED: '检查通过',
        PROGRAMMATIC_BLOCKED: '发现必须处理的问题', IN_PROGRESS: '正在生成', NEEDS_REVISION: '需要修改',
        READY_FOR_REVIEW: '待审核', CREATED: '待开始', DELIVERED: '已交付', CANCELLED: '已关闭'
      }[status] || ''
    },
    qualityStatusLabel(status) {
      return {
        NOT_RUN: '尚未检查', PASSED: '检查通过', PROGRAMMATIC_BLOCKED: '发现必须处理的问题',
        BLOCKED: '暂不能交付', READY: '可以进行最终复核',
        COMPLETED: '检查已完成，请核对评分与问题', RUNNING: '正在检查', PENDING: '等待检查', FAILED: '检查暂时失败'
      }[status] || '尚未检查'
    },
    qualityIssueLabel(type) {
      const labels = {
        MISSING_REPORT_CONTENT: '报告内容不完整', MISSING_SEMANTIC_SUPPORT: '内容缺少判断依据',
        SOURCE_COVERAGE_GAP: '部分内容缺少来源说明', DUPLICATE_CONTENT: '内容存在重复',
        UNSUPPORTED_CLAIM: '发现缺少依据的表述', INCONSISTENT_NARRATIVE: '前后表达不一致',
        SAFETY_LANGUAGE: '需要检查建议表达', USER_CONTEXT_MISMATCH: '内容与用户情况不匹配',
        FINDING_OVER_REPEATED: '同一专业判断被多段引用'
      }
      return labels[type] || '报告内容需要检查'
    },
    qualityIssueMessage(issue) {
      if (issue?.issue_type === 'FINDING_OVER_REPEATED') {
        return '有一条已确认判断出现在多个报告段落中。请核对各段是否各自承担不同作用，避免重复解释。'
      }
      return this.consultantText(issue?.message, '请查看对应报告内容并核对来源与表达。')
    },
    qualityIssueSuggestion(issue) {
      if (issue?.issue_type === 'FINDING_OVER_REPEATED') {
        return '如果各段分别用于介绍、解释和提出行动，可以保留；如果只是重复说明，可精简其中一段。'
      }
      return this.consultantText(issue?.suggestion, '请检查对应内容，确认后记录处理方式。')
    },
    issueLabel(type) {
      return this.qualityIssueLabel(type)
    },
    issueSeverityLabel(severity) {
      return { BLOCK: '必须处理', WARN: '建议处理', INFO: '提示' }[severity] || '提示'
    },
    consultantText(value, fallback = '请查看相关说明，并按建议处理。') {
      const text = String(value || '').trim()
      if (!text) return fallback
      if (/[A-Za-z]{2,}/.test(text)) return fallback
      return text
    },
    hasReference(value, key) {
      const refs = Array.isArray(value) ? value : String(value || '').split(/[\n,，]/)
      return refs.map(item => String(item).trim()).includes(key)
    },
    toggleReference(target, field, key, event) {
      const refs = String(target[field] || '').split(/[\n,，]/).map(item => item.trim()).filter(Boolean)
      const next = new Set(refs)
      if (event.target.checked) next.add(key)
      else next.delete(key)
      target[field] = [...next].join('\n')
    },
    staffErrorText(error) {
      const text = errorText(error)
      if (/^[a-z][a-z0-9_]+$/.test(String(text)) || /[A-Za-z]{3,}/.test(String(text))) {
        const messages = {
          report_analysis_finding_reference_invalid: '分析建议引用的资料已变化。请刷新页面后重新生成建议。',
          report_case_not_found: '未找到这份报告申请，请返回列表刷新后重试。',
          report_case_step_not_active: '当前步骤已变化，请刷新后继续处理。',
          report_analysis_output_required: '请先确认专业判断或分析内容，再完成本步骤。',
          report_analysis_sop_coverage_required: '请按本节点分析清单逐项审核。缺少资料的条目也需记录暂缓原因。'
        }
        return messages[text] || '操作暂时无法完成，请刷新页面后重试。'
      }
      return text
    },
    errorText(error) {
      return this.staffErrorText(error)
    },
    consultationTypeLabel,
    genderLabel,
    topicLabel,
    requestGoal,
    formatDate,
    pretty: prettyJson
  }
}
