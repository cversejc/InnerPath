import { authState } from '../../../stores/auth'
import { getCurrentUser } from '../../users/service.js'
import { getUserReports } from '../../reports/api.js'
import { createCalendarRequest, getCalendarRequests, retryCalendarRequest } from '../api.js'
import {
  buildCalendarRequestPayload,
  defaultThirtyDayRange,
  isThirtyDayRange
} from '../calendar-request-payload.js'

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
        this.scheduleCalendarPolling()
      } catch (error) {
        this.profile = this.profile || authState.user
        this.calendarRequests = []
        this.reports = []
      }
    },
  openCalendarRequest() {
      if (!this.calendarRequestDraft.source_report_id) {
        this.goToReports()
        return
      }
      this.calendarRequestError = ''
      this.calendarRequestFeedback = ''
      if (!this.reports.length) {
        this.calendarRequestError = '请先申请报告，并等待咨询师交付后再生成日历。'
        return
      }
      this.showCalendarRequestForm = true
      this.calendarRequestDraft.profile_version = this.profile?.profile_version || authState.user?.profile_version || 1
      if (!this.calendarRequestDraft.start_date || !this.calendarRequestDraft.end_date) {
        Object.assign(this.calendarRequestDraft, defaultThirtyDayRange())
      }
      if (!this.reports.some(report => report.id === Number(this.calendarRequestDraft.source_report_id))) {
        this.calendarRequestDraft.source_report_id = this.reports[0]?.id || ''
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
  goToReports() {
      this.$router.push({ path: '/pages/user/user', query: { tab: 'reports' } })
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
      if (!draft.source_report_id) return '请从一份已交付报告进入日历生成。'
      if (!draft.start_date || !draft.end_date) return '请选择完整的日历周期。'
      if (draft.start_date > draft.end_date) return '日历开始日期不能晚于结束日期。'
      if (!isThirtyDayRange(draft.start_date, draft.end_date)) return '日历周期需要连续 30 天。'
      if (!this.reports.some(report => report.id === Number(draft.source_report_id))) return '请先选择一份已交付报告。'
      if (!draft.usage_scenario) return '请选择日历用途。'
      if (!draft.focus_topics.length) return '至少选择一个关注领域。'
      if (!draft.goal.trim()) return '请填写当前决策目标。'
      if (!draft.expected_outcomes.length) return '至少选择一个期望输出。'
      if (!Number.isInteger(Number(draft.available_minutes_per_day)) || Number(draft.available_minutes_per_day) < 5 || Number(draft.available_minutes_per_day) > 480) return '每日可投入时间需在 5–480 分钟之间。'
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
        this.calendarRequestFeedback = created.calendar_id
          ? `已基于报告 #${created.source_report_id} 生成日历 #${created.calendar_id}。`
          : '已提交生成。你可以离开页面，回来后继续查看进度。'
        this.showCalendarRequestForm = false
        this.calendarRequestDraft = {
          profile_version: this.profile?.profile_version || 1,
          source_report_id: this.calendarRequestDraft.source_report_id,
          ...defaultThirtyDayRange(),
          focus_topics: [],
          usage_scenario: '',
          goal: '',
          expected_outcomes: [],
          available_minutes_per_day: 30,
          decision_description: '',
          additional_info: ''
        }
        await this.loadCalendar()
        await this.loadCalendarRequestData()
      } catch (error) {
        this.calendarRequestError = error.response?.data?.detail || '申请提交失败，请稍后再试。'
        await this.loadCalendarRequestData()
      } finally {
        this.submittingCalendarRequest = false
      }
    },
  scheduleCalendarPolling() {
      clearTimeout(this.calendarPollTimer)
      if (this.calendarPollingDisposed) return
      if (!this.calendarRequests.some(item => ['queued', 'generating', 'processing'].includes(item.status))) return
      this.calendarPollTimer = window.setTimeout(async () => {
        try {
          const old = this.calendarRequests
          const response = await getCalendarRequests()
          if (this.calendarPollingDisposed) return
          this.calendarRequests = response.items || []
          if (this.calendarRequests.some(item => ['fulfilled', 'delivered'].includes(item.status) && !['fulfilled', 'delivered'].includes(old.find(row => row.id === item.id)?.status))) {
            this.calendarRequestFeedback = '日历已生成并交付，可以选择日期查看建议。'
            await this.loadCalendar()
          }
        } catch (error) {
          this.calendarRequestError = '进度暂时读取失败，正在重试。'
        }
        this.scheduleCalendarPolling()
      }, 5000)
    },
  async retryCalendarGeneration(requestId) {
      if (this.submittingCalendarRequest) return
      this.submittingCalendarRequest = true
      try {
        await retryCalendarRequest(requestId)
        await this.loadCalendarRequestData()
        this.calendarRequestFeedback = '已使用原报告、资料和技能版本重新生成。'
      } catch (error) {
        this.calendarRequestError = error.response?.data?.detail || '重试失败，请稍后再试。'
      } finally {
        this.submittingCalendarRequest = false
      }
    },
}
