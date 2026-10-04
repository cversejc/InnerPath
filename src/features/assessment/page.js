import { getLatestReportContext, getLatestReportTask, getUserReports } from '../reports/api.js'
import { getCurrentUser } from '../users/service.js'
import AssessmentProfileStep from './components/AssessmentProfileStep.vue'
import AssessmentContextStep from './components/AssessmentContextStep.vue'
import AssessmentResultStep from './components/AssessmentResultStep.vue'
import { createEmptyProfile, mapUserToProfile } from '../users/profile.js'
import {
  assessmentTopics,
  createEmptyAssessmentContext,
  decisionStyleOptions,
  expectedOutcomeOptions
} from './form.js'
import draftMethods from './methods/drafts.js'
import profileMethods from './methods/profile.js'
import contextMethods from './methods/context.js'
import reportMethods from './methods/report.js'
import navigationMethods from './methods/navigation.js'

export default {
  name: 'Assessment',
  components: { AssessmentProfileStep, AssessmentContextStep, AssessmentResultStep },
  data() {
    return {
      currentStep: 1,
      loadingProfile: true,
      savingProfile: false,
      submitting: false,
      isGenerating: false,
      genStep: 0,
      formMessage: '',
      contextMessage: '',
      showOptionalProfile: false,
      showAdvancedContext: false,
      hasExistingProfile: false,
      profileDraft: createEmptyProfile(),
      profileVersion: 1,
      profileLastConfirmedAt: null,
      profileErrors: {},
      contextDraft: createEmptyAssessmentContext(),
      contextErrors: {},
      draftStatus: '',
      draftRestored: false,
      draftSavedAt: null,
      lastContext: null,
      lastContextReportId: null,
      reportPreview: { energyType: '综合型', coreTraits: '独特的个人特质', talents: '多元发展' },
      generatedReport: null,
      currentReportId: null,
      latestReportStatus: 'none',
      latestReportTaskId: '',
      latestReportId: null,
      latestReportProgress: 0,
      topics: assessmentTopics,
      expectedOutcomeOptions,
      decisionStyleOptions
    }
  },
  computed: {
    profileErrorSummary() {
      return Object.values(this.profileErrors)
    },
    contextErrorSummary() {
      return Object.values(this.contextErrors)
    },
    currentStepLabel() {
      return ['个人档案', '本次问题', '生成说明书'][this.currentStep - 1] || '申请'
    },
    stepProgress() {
      return Math.round((this.currentStep / 3) * 100)
    }
  },
  watch: {
    profileDraft: { deep: true, handler: 'saveDraft' },
    contextDraft: { deep: true, handler: 'saveDraft' }
  },
  async mounted() {
    try {
      const user = await getCurrentUser()
      this.profileDraft = mapUserToProfile(user)
      this.profileVersion = user.profile_version || 1
      this.profileLastConfirmedAt = user.profile_last_confirmed_at || null
      this.hasExistingProfile = Number(user.profile_completion || 0) >= 100
      this.currentStep = this.hasExistingProfile ? 2 : 1
      this.restoreDraft()
    } catch (error) {
      this.formMessage = error.response?.data?.detail || '暂时无法读取个人档案，请刷新后重试。'
    }
    const [contextResult, taskResult, reportsResult] = await Promise.allSettled([
      getLatestReportContext(),
      getLatestReportTask(),
      getUserReports(1, 1)
    ])
    if (contextResult.status === 'fulfilled') {
      const latest = contextResult.value
      if (latest?.context) {
        this.lastContext = latest.context
        this.lastContextReportId = latest.report_id
      }
    } else {
      console.warn('读取上次申请背景失败', contextResult.reason)
    }

    const latestTask = taskResult.status === 'fulfilled' ? taskResult.value : null
    const latestReport = reportsResult.status === 'fulfilled'
      ? reportsResult.value?.items?.[0]
      : null
    this.latestReportTaskId = latestTask?.task_id || ''
    this.latestReportProgress = Number(latestTask?.progress) || 0

    if (latestTask?.status === 'processing' && latestTask.task_id) {
      this.latestReportStatus = 'processing'
    } else {
      this.latestReportId = latestTask?.status === 'completed' && latestTask.report_id
        ? latestTask.report_id
        : latestReport?.id || null
      if (this.latestReportId) {
        this.latestReportStatus = 'completed'
        this.currentReportId = this.latestReportId
      } else if (latestTask?.status === 'failed') {
        this.latestReportStatus = 'failed'
      }
    }
    if (taskResult.status === 'rejected') {
      console.warn('读取最近报告任务失败', taskResult.reason)
    }
    if (reportsResult.status === 'rejected') {
      console.warn('读取最近报告失败', reportsResult.reason)
    }
    this.loadingProfile = false
  },
  methods: {
    ...draftMethods,
    ...profileMethods,
    ...contextMethods,
    ...reportMethods,
    ...navigationMethods
  }
}
