export function buildReportApplication(profile, context, profileVersion) {
  const listValue = value => Array.isArray(value) ? [...value] : []
  const textValue = value => String(value || '').trim() || null
  const timePrecision = profile.birth_time_precision || profile.time_accuracy || 'unknown'
  const contextSnapshot = {
    focus_topics: [...context.focus_topics],
    focus_topics_other: context.focus_topics_other,
    current_challenge: context.current_challenge,
    expected_outcomes: [...context.expected_outcomes],
    expected_outcomes_other: context.expected_outcomes_other,
    issue_duration: context.issue_duration,
    impact_level: context.impact_level,
    decision_status: context.decision_status,
    decision_description: context.decision_description,
    decision_style: [...context.decision_style],
    decision_style_other: context.decision_style_other,
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
      birth_hour: timePrecision === 'unknown' ? null : Number(profile.birth_hour),
      birth_minute: timePrecision === 'unknown' ? null : Number(profile.birth_minute),
      birth_place: String(profile.birth_place || '').trim() || null,
      calendar_type: profile.calendar_type,
      time_accuracy: timePrecision,
      birth_time_precision: timePrecision,
      current_residence: textValue(profile.current_residence),
      marital_status: textValue(profile.marital_status),
      occupation_status: textValue(profile.occupation_status),
      highest_education: textValue(profile.highest_education),
      mbti: textValue(profile.mbti),
      personality_keywords: listValue(profile.personality_keywords),
      strengths: textValue(profile.strengths),
      limitations: textValue(profile.limitations),
      mingli_experience: listValue(profile.mingli_experience),
      mingli_experience_other: textValue(profile.mingli_experience_other),
      mingli_attitude: textValue(profile.mingli_attitude),
      preferred_content_depth: textValue(profile.preferred_content_depth),
      default_usage_scenarios: listValue(profile.default_usage_scenarios),
      default_usage_scenarios_other: textValue(profile.default_usage_scenarios_other)
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
