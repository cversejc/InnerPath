import { generateReportWithAI, getLatestReportContext } from '../../utils/aiService.js'
import { getCurrentUser, updateUserProfile } from '../../utils/authService.js'
import { setAuthenticatedUser } from '../../stores/auth.js'
import ProfileFields from '../../components/ProfileFields.vue'
import ProfileSummary from '../../components/ProfileSummary.vue'
import { buildProfilePayload, createEmptyProfile, mapUserToProfile } from '../user-center/profile.js'
import {
  assessmentTopics,
  createEmptyAssessmentContext,
  decisionStyleOptions,
  expectedOutcomeOptions,
  validateAssessmentContext,
  validateAssessmentProfile
} from './form.js'

const STORAGE_KEY = 'assessment-intake-draft'

export default {
  name: 'Assessment',
  components: { ProfileFields, ProfileSummary },
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
      this.restoreDraft()
    } catch (error) {
      this.formMessage = error.response?.data?.detail || '暂时无法读取个人档案，请刷新后重试。'
    }
    try {
      const latest = await getLatestReportContext()
      if (latest?.context) {
        this.lastContext = latest.context
        this.lastContextReportId = latest.report_id
      }
    } catch (error) {
      // The report form remains usable if a legacy deployment has no context endpoint yet.
      console.warn('读取上次申请背景失败', error)
    } finally {
      this.loadingProfile = false
    }
  },
  methods: {
    saveDraft() {
      if (this.loadingProfile) return
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ profileVersion: this.profileVersion, profile: this.profileDraft, context: this.contextDraft }))
        this.draftSavedAt = new Date()
        this.draftStatus = '草稿已自动保存 · 刚刚'
      } catch {
        // Draft recovery is a convenience; it should never block form input.
      }
    },
    restoreDraft() {
      try {
        const stored = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null')
        if (!stored) return
        if (stored.profileVersion === this.profileVersion && stored.profile) {
          this.profileDraft = { ...this.profileDraft, ...stored.profile }
          this.draftRestored = true
        }
        if (stored.context) {
          this.contextDraft = { ...createEmptyAssessmentContext(), ...stored.context }
          this.draftRestored = true
        }
      } catch {
        sessionStorage.removeItem(STORAGE_KEY)
      }
    },
    validateProfile() {
      const errors = validateAssessmentProfile(this.profileDraft)
      this.profileErrors = errors
      return Object.keys(errors).length === 0
    },
    async saveProfileAndContinue() {
      this.formMessage = ''
      if (!this.validateProfile()) {
        this.formMessage = '请先补充个人档案中的必填项。'
        this.focusStepHeading()
        return
      }
      this.savingProfile = true
      try {
        const user = await updateUserProfile(buildProfilePayload(this.profileDraft))
        setAuthenticatedUser(user)
        this.profileDraft = mapUserToProfile(user)
        this.profileVersion = user.profile_version || this.profileVersion
        this.profileLastConfirmedAt = user.profile_last_confirmed_at || null
        this.hasExistingProfile = true
        this.draftStatus = `档案已确认 · 版本 v${this.profileVersion}`
        this.currentStep = 2
        this.focusStepHeading()
      } catch (error) {
        this.formMessage = error.response?.data?.detail || '档案保存失败，请检查网络后重试。'
      } finally {
        this.savingProfile = false
      }
    },
    editProfile() {
      this.formMessage = ''
      this.currentStep = 1
      this.focusStepHeading()
    },
    toggleTopic(topicId) {
      const topics = [...this.contextDraft.focus_topics]
      const index = topics.indexOf(topicId)
      if (index >= 0) topics.splice(index, 1)
      else if (topics.length < 3) topics.push(topicId)
      this.contextDraft.focus_topics = topics
      if (topics.length) delete this.contextErrors.focus_topics
    },
    toggleExpectedOutcome(value) {
      const outcomes = [...this.contextDraft.expected_outcomes]
      const index = outcomes.indexOf(value)
      if (index >= 0) outcomes.splice(index, 1)
      else if (outcomes.length < 7) outcomes.push(value)
      this.contextDraft.expected_outcomes = outcomes
      if (outcomes.length) delete this.contextErrors.expected_outcomes
    },
    toggleDecisionStyle(value) {
      const styles = [...this.contextDraft.decision_style]
      const index = styles.indexOf(value)
      if (index >= 0) styles.splice(index, 1)
      else if (styles.length < 6) styles.push(value)
      this.contextDraft.decision_style = styles
    },
    validateContextField(field) {
      if (field === 'current_challenge' && String(this.contextDraft.current_challenge || '').trim()) delete this.contextErrors.current_challenge
    },
    validateContext() {
      const errors = validateAssessmentContext(this.contextDraft)
      this.contextErrors = errors
      return Object.keys(errors).length === 0
    },
    reusePreviousContext() {
      this.contextDraft = { ...createEmptyAssessmentContext(), ...(this.lastContext || {}), focus_topics: [...(this.lastContext?.focus_topics || [])], expected_outcomes: [...(this.lastContext?.expected_outcomes || [])], decision_style: [...(this.lastContext?.decision_style || [])] }
      this.contextMessage = this.lastContextReportId ? `已带入报告 #${this.lastContextReportId} 的背景，请按这一次的情况编辑。` : '已带入上次背景，请按这一次的情况编辑。'
      this.$nextTick(() => document.getElementById('assessment-current-challenge')?.focus())
    },
    async submitAssessment() {
      if (this.submitting) return
      this.formMessage = ''
      if (!this.validateContext()) {
        this.formMessage = '请先补充本次申请的必填信息。'
        this.showAdvancedContext = true
        this.focusStepHeading()
        return
      }
      this.submitting = true
      this.currentStep = 3
      this.isGenerating = true
      this.focusStepHeading()
      try {
        this.genStep = 1
        await new Promise(resolve => setTimeout(resolve, 350))
        this.genStep = 2
        this.generatedReport = await generateReportWithAI({ profile_version: this.profileVersion, context: this.contextDraft })
        this.genStep = 3
        await new Promise(resolve => setTimeout(resolve, 350))
        this.genStep = 4
        this.reportPreview = {
          energyType: this.generatedReport.energyProfile?.type || '综合型',
          coreTraits: this.generatedReport.energyProfile?.coreTraits || '独特的个人特质',
          talents: Array.isArray(this.generatedReport.careerGuidance?.suitablePaths) ? this.generatedReport.careerGuidance.suitablePaths.join('、') : '多元发展'
        }
        await new Promise(resolve => setTimeout(resolve, 350))
        this.currentReportId = this.generatedReport.id
        this.isGenerating = false
        sessionStorage.removeItem(STORAGE_KEY)
        this.draftStatus = ''
        this.draftRestored = false
      } catch (error) {
        console.error('报告生成失败:', error)
        this.formMessage = error.response?.data?.detail || error.message || '报告生成失败，请检查网络后重试。'
        this.currentStep = 2
        this.isGenerating = false
        this.focusStepHeading()
      } finally {
        this.submitting = false
      }
    },
    focusStepHeading() {
      this.$nextTick(() => {
        const heading = Array.isArray(this.$refs.stepHeading) ? this.$refs.stepHeading[0] : this.$refs.stepHeading
        if (!heading) return
        window.scrollTo({ top: 0, behavior: 'auto' })
        heading.focus({ preventScroll: true })
      })
    },
    truncate(value, length) {
      const text = String(value || '')
      return text.length > length ? `${text.slice(0, length)}…` : text
    },
    viewFullReport() {
      if (this.currentReportId) this.$router.push(`/pages/report/detail?id=${this.currentReportId}`)
    },
    goToCalendar() {
      this.$router.push('/pages/calendar/calendar')
    }
  }
}
