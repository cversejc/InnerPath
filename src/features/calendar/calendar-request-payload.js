export function defaultThirtyDayRange(today = new Date()) {
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  const end = new Date(start)
  end.setDate(end.getDate() + 29)
  const toDateKey = date => [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, '0'),
    String(date.getDate()).padStart(2, '0')
  ].join('-')

  return { start_date: toDateKey(start), end_date: toDateKey(end) }
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
