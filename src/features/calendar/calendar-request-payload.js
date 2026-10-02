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
