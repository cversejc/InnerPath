
import { authState } from '../stores/auth'
import { getCurrentUser } from '../utils/authService'
import {
  createCalendarRequest,
  createDecisionLog,
  deleteDecisionLog,
  getCalendarRequests,
  getMyCalendars,
  getMyDecisionLogs
} from '../features/calendar/api'
import CalendarRequestSection from '../features/calendar/components/CalendarRequestSection.vue'
import CalendarPlanningSection from '../features/calendar/components/CalendarPlanningSection.vue'
import {
  calendarMeta as mockCalendarMeta,
  cautionNotes as mockCautionNotes,
  createCalendarDays as createMockCalendarDays,
  decisionNodes as mockDecisionNodes,
  phaseDefinitions as mockPhaseDefinitions,
  recordPrompts as mockRecordPrompts
} from '../data/decisionCalendar'

import requestsMethods from '../features/calendar/methods/requests.js'
import calendarDataMethods from '../features/calendar/methods/calendarData.js'
import selectionMethods from '../features/calendar/methods/selection.js'
import recordsMethods from '../features/calendar/methods/records.js'

const weekdays = ['日', '一', '二', '三', '四', '五', '六']
const DECISION_LOG_STORAGE_KEY = 'innerseek:decision-logs'
const mobileDetailMediaQuery = typeof window === 'undefined' ? null : window.matchMedia('(max-width: 900px)')
const allowDemoCalendar = import.meta.env.DEV && import.meta.env.VITE_DEMO_CALENDAR === 'true'

function createRecordDraft() {
  return {
    kind: 'action',
    status: 'done',
    content: '',
    note: ''
  }
}

function parseDateKey(value) {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function formatDateKey(date) {
  const pad = value => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function isToday(dateKey) {
  return formatDateKey(new Date()) === dateKey
}

function createMockCalendar() {
  return {
    id: 'demo-calendar',
    user_id: null,
    title: mockCalendarMeta.title,
    start_date: mockCalendarMeta.startDate,
    end_date: mockCalendarMeta.endDate,
    status: 'published',
    entries: createMockCalendarDays().map((entry, index) => ({
      id: `demo-entry-${index + 1}`,
      entry_date: entry.date,
      day_pillar: entry.dayPillar || null,
      tone: entry.tone || null,
      status_label: entry.statusLabel || null,
      keyword: entry.keyword || null,
      summary: entry.summary || null,
      suitable: entry.suitable || [],
      unsuitable: entry.unsuitable || [],
      time_window: entry.timeWindow || null,
      phase_id: entry.phaseId || null,
      phase_label: entry.phaseLabel || null,
      is_phase: entry.isPhase || false
    }))
  }
}

function dateKeyFromLabel(label, year) {
  const [, month, day] = label.match(/(\d+)月(\d+)日/) || []
  if (!month || !day) return null
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

export default {
  name: 'Calendar',
  components: { CalendarPlanningSection, CalendarRequestSection },
  data() {
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
      calendarRequests: [],
      showCalendarRequestForm: false,
      submittingCalendarRequest: false,
      calendarRequestError: '',
      calendarRequestFeedback: '',
      calendarRequestDraft: {
        profile_version: null,
        start_date: '',
        end_date: '',
        focus_topics: [],
        usage_scenario: '',
        goal: '',
        expected_outcomes: [],
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
    selectedDay() {
      return this.days.find(day => day.date === this.selectedDate) || this.days[0] || {}
    },
    selectedEntry() {
      return this.selectedDay
    },
    actionClimate() {
      const climateByTone = {
        green: { label: '推进窗口', caption: '适合把已经想清楚的事做成。', position: 84 },
        'green-yellow': { label: '先推进，再收束', caption: '上午打开行动，后半天留一点余地。', position: 72 },
        'yellow-green': { label: '先准备，再行动', caption: '先把信息理顺，下午再迈出下一步。', position: 58 },
        yellow: { label: '观察与准备', caption: '今天更适合整理判断，而不是急着拍板。', position: 45 },
        'red-yellow': { label: '缓冲后再判断', caption: '先降低消耗，等思路重新变得清楚。', position: 29 },
        red: { label: '先收气', caption: '今天更适合减少消耗，为下一次行动留力。', position: 16 },
        rest: { label: '先收气', caption: '今天更适合减少消耗，为下一次行动留力。', position: 16 }
      }
      return climateByTone[this.selectedEntry.tone] || climateByTone.yellow
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
  async mounted() {
    window.addEventListener('keydown', this.handleEscape)
    mobileDetailMediaQuery?.addEventListener('change', this.handleLayoutChange)
    await this.loadCalendar()
    await this.loadDecisionLogs()
    await this.loadCalendarRequestData()
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.handleEscape)
    mobileDetailMediaQuery?.removeEventListener('change', this.handleLayoutChange)
    document.body.classList.remove('dialog-open')
  },
  methods: {
    ...requestsMethods,
    ...calendarDataMethods,
    ...selectionMethods,
    ...recordsMethods,
    updateRecordDraft(patch) {
      this.recordDraft = { ...this.recordDraft, ...patch }
    }
  }
}
