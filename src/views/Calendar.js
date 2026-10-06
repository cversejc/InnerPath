
import CalendarRequestSection from '../features/calendar/components/CalendarRequestSection.vue'
import CalendarPlanningSection from '../features/calendar/components/CalendarPlanningSection.vue'
import { Button as VanButton } from 'vant'
import { isToday, parseDateKey } from '../features/calendar/helpers.js'
import requestsMethods from '../features/calendar/methods/requests.js'
import calendarDataMethods from '../features/calendar/methods/calendarData.js'
import selectionMethods from '../features/calendar/methods/selection.js'
import recordsMethods, { createRecordDraft } from '../features/calendar/methods/records.js'
import { confirmAction } from '../utils/confirmAction.js'
import {
  buildCalendarRequestPayload,
  defaultThirtyDayRange
} from '../features/calendar/calendar-request-payload.js'

const mobileDetailMediaQuery = typeof window === 'undefined' ? null : window.matchMedia('(max-width: 900px)')

export default {
  name: 'Calendar',
  components: { CalendarPlanningSection, CalendarRequestSection, VanButton },
  data() {
    const sourceReportId = Number(this.$route.query.source_report_id || this.$route.query.sourceReportId)
    const hasSourceReport = Number.isSafeInteger(sourceReportId) && sourceReportId > 0
    const initialRange = defaultThirtyDayRange()
    return {
      loading: true,
      calendar: null,
      calendarSource: 'api',
      calendarError: '',
      meta: {},
      phases: [],
      days: [],
      weekdays: ['一', '二', '三', '四', '五', '六', '日'],
      selectedDate: null,
      todayDate: null,
      isMobileLayout: mobileDetailMediaQuery?.matches ?? false,
      mobileDetailOpen: false,
      decisionNodes: [],
      recordPrompts: [],
      cautionNotes: ['', '', '今天不需要做到完美，只需要完成一件真正重要的事。'],
      decisionLogs: [],
      recordSource: 'local',
      showRecordForm: false,
      showFullGuidance: false,
      recordDraft: createRecordDraft(),
      recordError: '',
      recordFeedback: '',
      savingRecord: false,
      profile: null,
      reports: [],
      calendarRequests: [],
      calendarPollTimer: null,
      calendarPollingDisposed: false,
      showCalendarRequestForm: hasSourceReport,
      submittingCalendarRequest: false,
      calendarRequestError: '',
      calendarRequestFeedback: '',
      calendarRequestDraft: {
        profile_version: null,
        source_report_id: hasSourceReport ? sourceReportId : null,
        start_date: hasSourceReport ? initialRange.start_date : '',
        end_date: hasSourceReport ? initialRange.end_date : '',
        focus_topics: [],
        usage_scenario: '',
        goal: '',
        expected_outcomes: [],
        available_minutes_per_day: 30,
        decision_description: '',
        additional_info: ''
      },
      calendarTopicOptions: [
        { value: 'career', label: '事业发展' },
        { value: 'relationship', label: '感情关系' },
        { value: 'family', label: '家庭议题' },
        { value: 'finance', label: '财务规划' },
        { value: 'health', label: '身心健康' },
        { value: 'social', label: '人际关系' },
        { value: 'self', label: '个人成长' },
        { value: 'children', label: '子女教育' },
        { value: 'other', label: '其他' }
      ],
      calendarUsageOptions: [
        { value: 'morning_planning', label: '每天早上规划一天' },
        { value: 'evening_review', label: '每天晚上复盘反思' },
        { value: 'when_confused', label: '遇到困惑时查找指引' },
        { value: 'before_decision', label: '做重要决策前参考' },
        { value: 'emotional_support', label: '情绪低落时寻求安慰' },
        { value: 'other', label: '其他' }
      ],
      calendarOutcomeOptions: [
        { value: 'action_windows', label: '看见适合推进的时间' },
        { value: 'pause_windows', label: '知道什么时候适合观察或休整' },
        { value: 'daily_prompt', label: '获得每日行动提示' },
        { value: 'decision_review', label: '在重要决策前获得参考' },
        { value: 'reflection', label: '记录并复盘真实选择' },
        { value: 'emotional_support', label: '获得稳定情绪的提醒' },
        { value: 'other', label: '其他' }
      ]
    }
  },
  computed: {
    monthlySections() {
      const labels = { growth_task: '成长任务', resource: '可调用资源', old_pattern: '易激活的旧模式',
        decision_principle: '决定原则', rhythm_changes: '节奏变化' }
      return Object.entries(labels).map(([key, label]) => ({ key, label, content: this.meta.monthly?.[key] }))
        .filter(section => section.content)
    },
    selectedDay() {
      return this.days.find(day => day.date === this.selectedDate) || this.days[0] || {}
    },
    selectedEntry() {
      return this.selectedDay
    },
    actionClimate() {
      const climateByTone = {
        blue: { label: '探索窗口', caption: '用小规模尝试打开新的可能。', position: 65 },
        green: { label: '推进窗口', caption: '适合把已经想清楚的事做成。', position: 84 },
        'green-yellow': { label: '先推进，再收束', caption: '上午打开行动，后半天留一点余地。', position: 72 },
        'yellow-green': { label: '先准备，再行动', caption: '先把信息理顺，下午再迈出下一步。', position: 58 },
        yellow: { label: '观察与准备', caption: '今天更适合整理判断，而不是急着拍板。', position: 45 },
        'red-yellow': { label: '缓冲后再判断', caption: '先降低消耗，等思路重新变得清楚。', position: 29 },
        red: { label: '先收气', caption: '今天更适合减少消耗，为下一次行动留力。', position: 16 },
        rest: { label: '先收气', caption: '今天更适合减少消耗，为下一次行动留力。', position: 16 }
      }
      const climate = climateByTone[this.selectedEntry.tone] || climateByTone.yellow
      return { ...climate, caption: this.selectedEntry.tone_explanation || climate.caption }
    },
    visibleSuitable() {
      return this.showFullGuidance ? this.selectedEntry.suitable : this.selectedEntry.suitable.slice(0, 2)
    },
    visibleUnsuitable() {
      return this.showFullGuidance ? this.selectedEntry.unsuitable : this.selectedEntry.unsuitable.slice(0, 1)
    },
    hiddenGuidanceCount() {
      if (this.showFullGuidance) return 0
      return Math.max(0, this.selectedEntry.suitable.length - 2) + Math.max(0, this.selectedEntry.unsuitable.length - 1)
    },
    rhythmSegments() {
      if (this.selectedEntry.windows?.length) return this.selectedEntry.windows.map(window => ({ ...window, tone: this.selectedEntry.tone }))
      const rhythmByTone = {
        green: [['上午', '聚焦', 'green'], ['下午', '推进', 'green'], ['晚上', '收束', 'yellow']],
        'green-yellow': [['上午', '表达', 'green'], ['下午', '推进', 'green'], ['晚上', '收束', 'yellow']],
        'yellow-green': [['上午', '观察', 'yellow'], ['下午', '启动', 'green'], ['晚上', '整理', 'yellow']],
        yellow: [['上午', '观察', 'yellow'], ['下午', '准备', 'yellow'], ['晚上', '轻推', 'green']],
        'red-yellow': [['上午', '缓冲', 'red'], ['下午', '整理', 'yellow'], ['晚上', '收气', 'red']],
        red: [['上午', '收气', 'red'], ['下午', '整理', 'yellow'], ['晚上', '休息', 'red']],
        rest: [['上午', '收气', 'red'], ['下午', '整理', 'yellow'], ['晚上', '休息', 'red']]
      }
      return (rhythmByTone[this.selectedEntry.tone] || rhythmByTone.yellow).map(([period, label, tone]) => ({ period, label, tone }))
    },
    selectedRecords() {
      return this.decisionLogs.filter(record => record.date === this.selectedDate)
    },
    recordCountByDate() {
      return this.decisionLogs.reduce((counts, record) => {
        counts[record.date] = (counts[record.date] || 0) + 1
        return counts
      }, {})
    },
    monthRecordCount() {
      return this.decisionLogs.filter(record => this.days.some(day => day.date === record.date)).length
    },
    monthRecordDays() {
      return new Set(this.decisionLogs.filter(record => this.days.some(day => day.date === record.date)).map(record => record.date)).size
    },
    calendarLabel() {
      if (!this.calendar) return ''
      const start = this.calendar.start_date || this.days[0]?.date
      const end = this.calendar.end_date || this.days[this.days.length - 1]?.date
      if (!start || !end) return '个人日历'
      return `${start.slice(0, 7).replace('-', ' / ')}—${end.slice(0, 7).replace('-', ' / ')}`
    },
    calendarCells() {
      if (!this.days.length) return []
      const firstDate = parseDateKey(this.days[0].date)
      const leading = (firstDate.getDay() + 6) % 7
      const trailing = (7 - ((leading + this.days.length) % 7)) % 7
      const emptyCells = Array.from({ length: leading + trailing }, (_, index) => ({
        key: `empty-${index}`,
        empty: true
      }))
      return [
        ...emptyCells.slice(0, leading),
        ...this.days.map(day => ({
          ...day,
          key: day.date,
          isCurrentDay: isToday(day.date),
          recordCount: this.recordCountByDate[day.date] || 0
        })),
        ...emptyCells.slice(leading)
      ]
    }
  },
  watch: {
    'calendarRequestDraft.start_date'(start) {
      this.setCalendarEndDate(start)
    },
    '$route.query.generate'(requested) {
      if (requested === '1' && this.reports.length) this.openCalendarRequest()
    }
  },
  async mounted() {
    window.addEventListener('keydown', this.handleEscape)
    mobileDetailMediaQuery?.addEventListener('change', this.handleLayoutChange)
    await this.loadCalendar()
    await this.loadDecisionLogs()
    await this.loadCalendarRequestData()
  },
  beforeUnmount() {
    this.calendarPollingDisposed = true
    clearTimeout(this.calendarPollTimer)
    window.removeEventListener('keydown', this.handleEscape)
    mobileDetailMediaQuery?.removeEventListener('change', this.handleLayoutChange)
    document.body.classList.remove('dialog-open')
  },
  methods: {
    confirmAction,
    ...requestsMethods,
    ...calendarDataMethods,
    ...selectionMethods,
    ...recordsMethods,
    updateRecordDraft(patch) {
      this.recordDraft = { ...this.recordDraft, ...patch }
    }
  }
}
