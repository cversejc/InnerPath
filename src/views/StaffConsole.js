import { hasRole } from '../stores/auth'
import { Button as VanButton, Dialog as VanDialog, Field as VanField } from 'vant'
import {
  SERVICE_REQUEST_STATUS_LABELS,
  birthSummary as formatBirthSummary,
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
import assignmentMethods from '../features/service-requests/methods/assignment.js'
import queueMethods from '../features/service-requests/methods/queue.js'
import workflowMethods from '../features/service-requests/methods/workflow.js'
import reportCaseMethods from '../features/service-requests/methods/report-case.js'
import reportAnalysisMethods from '../features/service-requests/methods/report-analysis.js'
import ReportNodeWorkbench from '../features/report-cases/components/ReportNodeWorkbench.vue'
import AnalysisDraftsPanel from '../features/report-cases/components/AnalysisDraftsPanel.vue'
import { REPORT_STEP_STATUS_LABELS, reportStage } from '../features/report-cases/stages.js'
import { confirmAction } from '../utils/confirmAction.js'

export default {
  name: 'StaffConsole',
  components: { VanButton, VanDialog, VanField, ReportNodeWorkbench, AnalysisDraftsPanel },
  data() {
    const admin = hasRole('admin')
    return {
      admin,
      scope: admin ? 'all' : 'mine',
      scopeOptions: admin
        ? [{ id: 'all', label: '全部申请' }, { id: 'available', label: '待接单' }, { id: 'mine', label: '我的处理中' }]
        : [{ id: 'mine', label: '我的处理中' }, { id: 'available', label: '待接单' }],
      serviceType: '',
      statusFilter: '',
      statusOptions: ['submitted', 'accepted', 'ai_processing', 'ai_ready', 'reviewing', 'needs_info', 'failed', 'delivered'],
      requests: { total: 0, items: [] },
      selectedRequest: null,
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
      reportQualitySaving: false,
      reportCaseDelivering: false,
      finalGateAttested: false,
      reportCaseLoading: false,
      reportAnalysisSaving: false,
      reportAnalysisFindingSavingKey: '',
      reportAnalysisFragmentSavingKey: '',
      reportNarrativeSaving: false,
      reportNarrativePollTimer: null,
      narrativeCandidateDrafts: {},
      newReportWritingFragment: { fragment_key: '', title: '' },
      reportStepSaving: false,
      reportStepReturn: { visible: false, targetStepKey: '', reason: '' },
      editingFindingKey: null,
      reportFindingDraft: null,
      newReportFinding: { finding_key: '', claim: '', semantic_role: '', evidence_refs: '' },
      reportFindingSaving: false,
      reportFragmentDrafts: {},
      newReportFragment: { fragment_key: '', title: '', content: '', finding_refs: '', evidence_refs: '' },
      reportFragmentSaving: false,
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
      rejectDialog: { visible: false, reason: '', error: '' },
      rejectSaving: false,
      reportEditor: reportEditorFromPayload(),
      calendarEditor: calendarEditorFromPayload(),
      consultants: [],
      assignmentId: null,
      assignmentSaving: false
    }
  },
  computed: {
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
      if (this.scope === 'available') return '仅展示还未被接单的申请。'
      if (this.scope === 'mine') return '展示分配给当前咨询师的申请。'
      return '管理员可查看全量申请并介入处理。'
    },
    birthSummary() {
      return formatBirthSummary(this.workspace)
    },
    reportContentPlan() {
      return this.reportNarrative.current_plan?.plan_json?.content_plan || null
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
    }
  },
  mounted() {
    this.loadRequests()
    this.loadConsultants()
  },
  beforeUnmount() {
    this.stopPolling()
    if (this.reportNarrativePollTimer) clearTimeout(this.reportNarrativePollTimer)
  },
  methods: {
    confirmAction,
    ...queueMethods,
    ...workflowMethods,
    ...reportCaseMethods,
    ...reportAnalysisMethods,
    ...assignmentMethods,
    reportFragmentStatus(fragmentKey) {
      return this.reportCaseContent.fragments.find(item => item.fragment_key === fragmentKey)?.status || '待写作'
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
      return SERVICE_REQUEST_STATUS_LABELS[status] || status
    },
    reportStepLabel(stepKey) {
      return reportStage(stepKey)?.shortName || stepKey
    },
    reportStepStatusLabel(status) {
      return REPORT_STEP_STATUS_LABELS[status] || status
    },
    scrollToReportSection(sectionId) {
      document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    },
    genderLabel,
    topicLabel,
    requestGoal,
    formatDate,
    pretty: prettyJson,
    errorText
  }
}
