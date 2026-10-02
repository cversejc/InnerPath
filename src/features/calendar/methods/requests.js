import { authState } from '../../../stores/auth'
import { getCurrentUser } from '../../users/service.js'
import { createCalendarRequest, getCalendarRequests } from '../api.js'
import { buildCalendarRequestPayload } from '../calendar-request-payload.js'

export default {
  async loadCalendarRequestData() {
      try {
        const [user, requestResponse] = await Promise.all([getCurrentUser(), getCalendarRequests()])
        this.profile = user
        this.calendarRequestDraft.profile_version = user.profile_version || 1
        this.calendarRequests = requestResponse.items || []
      } catch (error) {
        this.profile = this.profile || authState.user
        this.calendarRequests = []
      }
    },
  openCalendarRequest() {
      this.calendarRequestError = ''
      this.calendarRequestFeedback = ''
      this.showCalendarRequestForm = true
      this.calendarRequestDraft.profile_version = this.profile?.profile_version || authState.user?.profile_version || 1
      this.$nextTick(() => document.getElementById('calendar-request-start')?.focus())
    },
  closeCalendarRequest() {
      this.showCalendarRequestForm = false
      this.calendarRequestError = ''
    },
  goToProfile() {
      this.$router.push({ path: '/pages/user/user', query: { tab: 'settings' } })
    },
  toggleCalendarTopic(value) {
      const topics = [...this.calendarRequestDraft.focus_topics]
      const index = topics.indexOf(value)
      if (index >= 0) topics.splice(index, 1)
      else if (topics.length < 3) topics.push(value)
      this.calendarRequestDraft.focus_topics = topics
    },
  toggleCalendarOutcome(value) {
      const outcomes = [...this.calendarRequestDraft.expected_outcomes]
      const index = outcomes.indexOf(value)
      if (index >= 0) outcomes.splice(index, 1)
      else if (outcomes.length < 7) outcomes.push(value)
      this.calendarRequestDraft.expected_outcomes = outcomes
    },
  validateCalendarRequest() {
      const draft = this.calendarRequestDraft
      if (!this.profile || Number(this.profile.profile_completion || 0) < 100) return '请先完成个人档案中的性别和出生日期。'
      if (!draft.start_date || !draft.end_date) return '请选择完整的日历周期。'
      if (draft.start_date > draft.end_date) return '日历开始日期不能晚于结束日期。'
      if (!draft.usage_scenario) return '请选择日历用途。'
      if (!draft.focus_topics.length) return '至少选择一个关注领域。'
      if (!draft.goal.trim()) return '请填写当前决策目标。'
      if (!draft.expected_outcomes.length) return '至少选择一个期望输出。'
      return ''
    },
  async submitCalendarRequest() {
      if (this.submittingCalendarRequest) return
      this.calendarRequestError = ''
      this.calendarRequestFeedback = ''
      const validationError = this.validateCalendarRequest()
      if (validationError) {
        this.calendarRequestError = validationError
        return
      }
      this.submittingCalendarRequest = true
      try {
        const created = await createCalendarRequest(
          buildCalendarRequestPayload(
            this.calendarRequestDraft,
            this.profile?.profile_version || 1
          )
        )
        this.calendarRequests = [created, ...this.calendarRequests]
        this.calendarRequestFeedback = '申请已提交，后台会按你的档案版本审核。'
        this.calendarRequestDraft = {
          profile_version: this.profile?.profile_version || 1,
          source_report_id: this.calendarRequestDraft.source_report_id,
          start_date: '',
          end_date: '',
          focus_topics: [],
          usage_scenario: '',
          goal: '',
          expected_outcomes: [],
          decision_description: '',
          additional_info: ''
        }
      } catch (error) {
        this.calendarRequestError = error.response?.data?.detail || '申请提交失败，请稍后再试。'
      } finally {
        this.submittingCalendarRequest = false
      }
    },
}
