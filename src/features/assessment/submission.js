export function buildReportApplication(profile, context, profileVersion) {
  const contextSnapshot = {
    focus_topics: [...context.focus_topics],
    current_challenge: context.current_challenge,
    expected_outcomes: [...context.expected_outcomes],
    issue_duration: context.issue_duration,
    impact_level: context.impact_level,
    decision_status: context.decision_status,
    decision_description: context.decision_description,
    decision_style: [...context.decision_style],
    additional_info: context.additional_info
  }

  return {
    service_type: 'report',
    profile: {
      name: String(profile.name || '').trim(),
      gender: profile.gender,
      birth_year: Number(profile.birth_year),
      birth_month: Number(profile.birth_month),
      birth_day: Number(profile.birth_day),
      birth_is_leap_month: Boolean(profile.calendar_type === 'lunar' && profile.birth_is_leap_month),
      birth_hour: profile.birth_time_precision === 'unknown' ? null : Number(profile.birth_hour),
      birth_minute: profile.birth_time_precision === 'unknown' ? null : Number(profile.birth_minute),
      birth_place: String(profile.birth_place || '').trim() || null,
      calendar_type: profile.calendar_type,
      time_accuracy: profile.birth_time_precision
    },
    profile_version: profileVersion,
    context: contextSnapshot,
    selected_topics: [...context.focus_topics],
    additional_info: [context.current_challenge, context.additional_info]
      .map(value => String(value || '').trim())
      .filter(Boolean)
      .join('\n\n') || null
  }
}

export function createIdempotencyKey() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  return `assessment-${Date.now()}-${Math.random().toString(36).slice(2)}`
}
