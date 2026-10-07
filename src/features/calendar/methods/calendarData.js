import { getMyCalendars } from '../api.js'
import {
  calendarMeta as mockCalendarMeta,
  cautionNotes as mockCautionNotes,
  createCalendarDays as createMockCalendarDays,
  decisionNodes as mockDecisionNodes,
  phaseDefinitions as mockPhaseDefinitions,
  recordPrompts as mockRecordPrompts
} from '../../../data/decisionCalendar.js'
import { dateKeyFromLabel, isToday, parseDateKey, weekdays } from '../helpers.js'
import { selectPublishedCalendar } from '../cover.js'
import { resolveCalendarPracticeRefs } from '../practice-actions.js'
import { calendarToneLabel } from '../../../utils/displayLabels.js'

const allowDemoCalendar = Boolean(import.meta.env?.DEV && import.meta.env?.VITE_DEMO_CALENDAR === 'true')

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

export default {
  async loadCalendar(fetchCalendars = getMyCalendars) {
    try {
      this.calendarError = ''
      const response = await fetchCalendars()
      const publishedCalendar = selectPublishedCalendar(response)
      if (publishedCalendar) {
        this.applyCalendar(publishedCalendar, 'api')
      } else if (allowDemoCalendar) {
        this.applyCalendar(createMockCalendar(), 'mock')
      } else {
        this.calendar = null
        this.calendarSource = 'empty'
        this.days = []
        this.meta = {}
      }
    } catch (error) {
      if (allowDemoCalendar) {
        this.calendarError = ''
        this.applyCalendar(createMockCalendar(), 'mock')
      } else {
        this.calendar = null
        this.calendarSource = 'empty'
        this.days = []
        this.meta = {}
        this.calendarError = '暂时无法读取已交付日历，请重新加载或稍后再试。'
      }
    } finally {
      this.loading = false
    }
  },
  async retryCalendarLoad() {
    this.loading = true
    await this.loadCalendar()
  },
  applyCalendar(calendar, source) {
      this.calendar = calendar
      this.calendarSource = source
      const calendarMeta = calendar.meta_payload || calendar.metaPayload || {}
      const practiceRhythm = calendarMeta.practice_rhythm || {}
      this.days = (calendar.entries || []).map(entry => {
        const entryDate = entry.entry_date || entry.date
        if (!entryDate) return null
        const date = parseDateKey(entryDate)
        const dailyDetails = calendarMeta.daily_details?.[entryDate] || {}
        return {
          ...entry,
          ...dailyDetails,
          date: entryDate,
          month: date.getMonth() + 1,
          day: date.getDate(),
          weekday: weekdays[date.getDay()],
          dayPillar: entry.day_pillar || entry.dayPillar || '',
          statusLabel: entry.status_label || entry.statusLabel || '',
          shortLabel: entry.keyword || entry.shortLabel || entry.status_label || entry.statusLabel || '查看',
          phaseId: entry.phase_id || entry.phaseId || entry.tone || 'default',
          phaseLabel: entry.phase_label || entry.phaseLabel || entry.status_label || entry.statusLabel || calendarToneLabel(entry.tone, ''),
          timeWindow: entry.time_window || entry.timeWindow || '按你的节奏安排，给决定留出换气空间。',
          suitable: entry.suitable || [],
          unsuitable: entry.unsuitable || [],
          linkedPractices: resolveCalendarPracticeRefs(dailyDetails.action_refs, practiceRhythm),
          unavailablePracticeCount: practiceRhythm.unavailable_actions?.length || 0,
          availableMinutesPerDay: calendarMeta.available_minutes_per_day || 30,
          isPhase: entry.is_phase ?? entry.isPhase ?? false
        }
      }).filter(Boolean)
      const startDate = calendar.start_date || this.days[0]?.date || ''
      const year = startDate.slice(0, 4)
      this.meta = source === 'mock'
        ? mockCalendarMeta
        : {
            title: calendar.title,
            subtitle: calendarMeta.subtitle || 'PERSONAL TIMEZONE',
            dateLabel: calendarMeta.dateLabel || `${startDate} — ${calendar.end_date || this.days[this.days.length - 1]?.date || ''}`,
            pillars: calendarMeta.pillars || '',
            rhythm: calendarMeta.rhythm || '少说，多做，多记录',
            intro: calendarMeta.intro || '这是一张属于你的决策时机参照系，帮你在重要选择前留出观察、行动与复盘的空间。',
            overview: Array.isArray(calendarMeta.overview) ? calendarMeta.overview : [],
            monthly: calendarMeta.monthly || null,
            limitations: Array.isArray(calendarMeta.limitations) ? calendarMeta.limitations : []
          }
      this.todayDate = this.days.find(day => isToday(day.date))?.date || this.days[0]?.date || null
      this.selectedDate = this.todayDate
      this.decisionNodes = source === 'mock'
        ? mockDecisionNodes.map(node => ({ ...node, dateKey: dateKeyFromLabel(node.date, year) }))
        : this.days.map(day => ({
            date: `${day.month}月${day.day}日`,
            dateKey: day.date,
            pillar: day.dayPillar || '—',
            tone: day.tone || 'yellow',
            type: day.keyword || day.statusLabel || '查看详情'
          }))
      this.phases = source === 'mock' ? mockPhaseDefinitions : this.buildPhases()
      this.recordPrompts = source === 'mock' ? mockRecordPrompts : []
      this.cautionNotes = source === 'mock' ? mockCautionNotes : ['', '', '今天不需要做到完美，只需要完成一件真正重要的事。']
      this.mobileDetailOpen = !this.isMobileLayout
    },
  buildPhases() {
      const grouped = []
      for (const day of this.days) {
        const sourceId = day.phaseId
        const existing = grouped[grouped.length - 1]
        if (existing?.sourceId === sourceId) {
          existing.endDate = day.date
          existing.dateRange = `${existing.startDate}—${existing.endDate}`
          day.phaseId = existing.id
        } else {
          day.phaseId = `${sourceId}:${day.date}`
          grouped.push({
            id: day.phaseId,
            sourceId,
            label: day.phaseLabel || day.shortLabel,
            tone: day.tone || 'yellow',
            startDate: day.date,
            endDate: day.date,
            dateRange: day.date
          })
        }
      }
      return grouped
    }
}
