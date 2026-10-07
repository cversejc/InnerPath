import { addDaysToDateKey, shanghaiDateKey } from '../../utils/dateTime.js'

export function defaultThirtyDayRange(today = new Date()) {
  const start = shanghaiDateKey(today)
  return { start_date: start, end_date: addDaysToDateKey(start, 29) }
}

export function isThirtyDayRange(startDate, endDate) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(startDate || '') || !/^\d{4}-\d{2}-\d{2}$/.test(endDate || '')) {
    return false
  }
  const start = Date.parse(`${startDate}T00:00:00Z`)
  const end = Date.parse(`${endDate}T00:00:00Z`)
  return Number.isFinite(start) && Number.isFinite(end) && end - start === 29 * 86400000
}

export function buildCalendarRequestPayload(draft, profileVersion) {
  const sourceReportId = Number(draft.source_report_id)
  return {
    ...draft,
    profile_version: profileVersion || draft.profile_version || 1,
    source_report_id: Number.isSafeInteger(sourceReportId) && sourceReportId > 0
      ? sourceReportId
      : null
  }
}
