import { calendarMeta, dailyDetails, phaseDefinitions } from '../../data/decisionCalendarContent.js'
import { formatDateKey, parseDateKey, weekdays } from './helpers.js'

function phaseForDate(dateKey) {
  return phaseDefinitions.find(phase => dateKey >= phase.startDate && dateKey <= phase.endDate)
}

export function getDateEntry(dateKey) {
  const phase = phaseForDate(dateKey)
  const daily = dailyDetails[dateKey]

  if (daily) {
    return {
      ...daily,
      phaseId: phase?.id,
      phaseLabel: phase?.label,
      isPhase: false
    }
  }

  if (!phase) {
    return null
  }

  return {
    ...phase,
    keyword: phase.id === 'rest' ? '积累' : phase.id === 'feedback' ? '反馈' : '调整',
    phaseId: phase.id,
    phaseLabel: phase.label,
    isPhase: true
  }
}

export function createCalendarDays() {
  const days = []
  const cursor = parseDateKey(calendarMeta.startDate)
  const end = parseDateKey(calendarMeta.endDate)

  while (cursor <= end) {
    const date = formatDateKey(cursor)
    const entry = getDateEntry(date)
    days.push({
      date,
      day: cursor.getDate(),
      month: cursor.getMonth() + 1,
      weekday: weekdays[cursor.getDay()],
      ...entry
    })
    cursor.setDate(cursor.getDate() + 1)
  }

  return days
}

export function resolveDefaultDate(now = new Date()) {
  const today = formatDateKey(now)

  if (today < calendarMeta.startDate) {
    return calendarMeta.startDate
  }

  if (today > calendarMeta.endDate) {
    return calendarMeta.endDate
  }

  return today
}
