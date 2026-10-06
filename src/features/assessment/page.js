import { getLatestReportContext } from '../reports/api.js'
import { getMyServiceRequests } from '../service-requests/api.js'
import { getCurrentUser } from '../users/service.js'
import { getMyServiceRequest } from '../service-requests/api.js'
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
      currentRequestId: null,
      submissionFingerprint: null,
      submissionIdempotencyKey: null,
      editingRequestId: null,
      reportIdempotencyKey: null,
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
      return ['个人档案', '本次问题', '申请已提交'][this.currentStep - 1] || '申请'
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
      this.restoreDraft()
      const requestId = Number(this.$route.query.requestId)
      if (requestId) {
        const request = await getMyServiceRequest(requestId)
        if (request.service_type !== 'report' || request.status !== 'needs_info') {
          this.formMessage = '这份报告申请当前不需要补充资料。'
        } else {
          const context = request.request_payload?.context || {}
          this.editingRequestId = request.id
          this.currentStep = 2
          this.contextDraft = {
            ...createEmptyAssessmentContext(),
            ...context,
            focus_topics: [...(context.focus_topics || [])],
            expected_outcomes: [...(context.expected_outcomes || [])],
            decision_style: [...(context.decision_style || [])]
          }
        }
      }
    } catch (error) {
      this.formMessage = error.response?.data?.detail || '暂时无法读取个人档案，请刷新后重试。'
    }
    try {
      const requests = await getMyServiceRequests({ service_type: 'report' })
      const latestRequest = requests.items?.[0]
      if (latestRequest?.request_payload?.context) {
        this.lastContext = latestRequest.request_payload.context
        this.lastContextReportId = latestRequest.id
      } else {
        const latest = await getLatestReportContext()
        if (latest?.context) {
          this.lastContext = latest.context
          this.lastContextReportId = latest.report_id
        }
      }
    } catch (error) {
      // The report form remains usable if a legacy deployment has no context endpoint yet.
      console.warn('读取上次申请背景失败', error)
    } finally {
      this.loadingProfile = false
    }
  },
  methods: {
    ...draftMethods,
    ...profileMethods,
    ...contextMethods,
    ...reportMethods,
    ...navigationMethods
  }
}
