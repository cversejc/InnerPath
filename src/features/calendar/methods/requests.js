import { authState } from '../../../stores/auth'
import { getCurrentUser } from '../../users/service.js'
import { getUserReports } from '../../reports/api.js'
import { createCalendarRequest, getCalendarRequests } from '../api.js'

export default {
  async loadCalendarRequestData() {
      try {
        const [user, requestResponse, reportResponse] = await Promise.all([
          getCurrentUser(),
          getCalendarRequests(),
          getUserReports(1, 100)
        ])
        this.profile = user
        this.calendarRequestDraft.profile_version = user.profile_version || 1
        this.calendarRequests = requestResponse.items || []
        this.reports = reportResponse.items || []
        const requestedReportId = Number(this.$route.query.sourceReportId)
        const requestedReport = this.reports.find(report => report.id === requestedReportId)
        this.calendarRequestDraft.source_report_id = requestedReport?.id || this.reports[0]?.id || ''
        if (this.$route.query.generate === '1' && this.reports.length) this.openCalendarRequest()
      } catch (error) {
        this.profile = this.profile || authState.user
        this.calendarRequests = []
        this.reports = []
      }
    },
  openCalendarRequest() {
      this.calendarRequestError = ''
      this.calendarRequestFeedback = ''
      if (!this.reports.length) {
        this.calendarRequestError = '请先申请报告，并等待咨询师交付后再生成日历。'
        return
      }
      this.showCalendarRequestForm = true
      this.calendarRequestDraft.profile_version = this.profile?.profile_version || authState.user?.profile_version || 1
      if (!this.reports.some(report => report.id === Number(this.calendarRequestDraft.source_report_id))) {
        this.calendarRequestDraft.source_report_id = this.reports[0].id
      }
      this.$nextTick(() => document.getElementById('calendar-request-start')?.focus())
    },
  setCalendarEndDate(start) {
      if (!start) {
        this.calendarRequestDraft.end_date = ''
        return
      }
      const end = new Date(`${start}T00:00:00`)
      if (Number.isNaN(end.getTime())) return
      end.setDate(end.getDate() + 29)
      this.calendarRequestDraft.end_date = `${end.getFullYear()}-${String(end.getMonth() + 1).padStart(2, '0')}-${String(end.getDate()).padStart(2, '0')}`
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
      if (!this.reports.some(report => report.id === Number(draft.source_report_id))) return '请先选择一份已交付报告。'
      if (!draft.start_date || !draft.end_date) return '请选择完整的日历周期。'
      if ((new Date(`${draft.end_date}T00:00:00`) - new Date(`${draft.start_date}T00:00:00`)) / 86400000 !== 29) return '日历周期需覆盖 30 天，请重新选择开始日期。'
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
        const created = await createCalendarRequest({
          ...this.calendarRequestDraft,
          source_report_id: Number(this.calendarRequestDraft.source_report_id),
          profile_version: this.profile?.profile_version || 1
        })
        this.calendarRequests = [created, ...this.calendarRequests]
        this.calendarRequestFeedback = '日历生成任务已启动，成功后会自动开放使用。'
        await this.$router.push(`/pages/requests/requests?submitted=${created.id}&kind=calendar`)
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
