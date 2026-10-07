import { shanghaiYear } from '../../utils/dateTime.js'

export function createEmptyProfile() {
  return {
    name: '',
    gender: '',
    contact: '',
    calendar_type: 'solar',
    birth_year: null,
    birth_month: null,
    birth_day: null,
    birth_is_leap_month: false,
    birth_hour: null,
    birth_minute: null,
    birth_place: '',
    birth_time_precision: 'unknown',
    current_residence: '',
    marital_status: '',
    occupation_status: '',
    highest_education: '',
    mbti: '',
    personality_keywords: [],
    strengths: '',
    limitations: '',
    mingli_experience: [],
    mingli_experience_other: '',
    mingli_attitude: '',
    preferred_content_depth: '',
    default_usage_scenarios: [],
    default_usage_scenarios_other: ''
  }
}

export function mapUserToProfile(user) {
  return {
    name: user.name || '',
    gender: user.gender || '',
    contact: user.phone || '',
    calendar_type: user.calendar_type || 'solar',
    birth_year: user.birth_year || null,
    birth_month: user.birth_month || null,
    birth_day: user.birth_day || null,
    birth_is_leap_month: Boolean(user.birth_is_leap_month),
    birth_hour: user.birth_hour ?? null,
    birth_minute: user.birth_minute ?? null,
    birth_place: user.birth_place || '',
    birth_time_precision: user.birth_time_precision || 'unknown',
    current_residence: user.current_residence || '',
    marital_status: user.marital_status || '',
    occupation_status: user.occupation_status || '',
    highest_education: user.highest_education || '',
    mbti: user.mbti || '',
    personality_keywords: Array.isArray(user.personality_keywords) ? [...user.personality_keywords] : [],
    strengths: user.strengths || '',
    limitations: user.limitations || '',
    mingli_experience: Array.isArray(user.mingli_experience) ? [...user.mingli_experience] : [],
    mingli_experience_other: user.mingli_experience_other || '',
    mingli_attitude: user.mingli_attitude || '',
    preferred_content_depth: user.preferred_content_depth || '',
    default_usage_scenarios: Array.isArray(user.default_usage_scenarios) ? [...user.default_usage_scenarios] : [],
    default_usage_scenarios_other: user.default_usage_scenarios_other || ''
  }
}

export function validateProfile(profile, currentYear = shanghaiYear()) {
  const errors = {}
  if (!String(profile.name || '').trim()) errors.name = '请填写称呼。'
  if (!profile.gender) errors.gender = '请选择性别。'

  const year = Number(profile.birth_year)
  const month = Number(profile.birth_month)
  const day = Number(profile.birth_day)
  if (!year || year < 1900 || year > currentYear) errors.birth_date = '请填写有效的出生年份。'
  if (!month || month < 1 || month > 12 || !day || day < 1 || day > 31) errors.birth_date = '请填写完整的出生日期。'
  if (profile.calendar_type === 'solar' && year && month && day) {
    if (profile.birth_is_leap_month) errors.birth_date = '公历日期不能选择闰月。'
    const date = new Date(Date.UTC(year, month - 1, day))
    if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) {
      errors.birth_date = '公历出生日期不存在，请检查日期。'
    }
  }
  if (
    profile.birth_time_precision !== 'unknown' &&
    (profile.birth_hour === null || profile.birth_hour === undefined || profile.birth_minute === null || profile.birth_minute === undefined)
  ) {
    errors.birth_time = '请选择完整的出生小时和分钟。'
  }

  return errors
}

export function buildProfilePayload(settings) {
  const profile = { ...settings }
  delete profile.contact
  profile.name = String(profile.name || '').trim()
  ;[
    'birth_place',
    'current_residence',
    'mbti',
    'strengths',
    'limitations',
    'mingli_experience_other',
    'marital_status',
    'occupation_status',
    'highest_education',
    'mingli_attitude',
    'preferred_content_depth',
    'default_usage_scenarios_other'
  ].forEach(field => {
    profile[field] = String(profile[field] || '').trim() || null
  })
  profile.mbti = String(profile.mbti || '').toUpperCase() || null
  ;['personality_keywords', 'mingli_experience', 'default_usage_scenarios'].forEach(field => {
    profile[field] = Array.isArray(profile[field]) ? profile[field] : []
  })
  if (!profile.mingli_experience.includes('other')) profile.mingli_experience_other = null
  if (!profile.default_usage_scenarios.includes('other')) profile.default_usage_scenarios_other = null
  profile.birth_year = profile.birth_year ? Number(profile.birth_year) : null
  profile.birth_month = profile.birth_month ? Number(profile.birth_month) : null
  profile.birth_day = profile.birth_day ? Number(profile.birth_day) : null
  profile.birth_is_leap_month = Boolean(
    profile.calendar_type === 'lunar' && profile.birth_is_leap_month
  )
  profile.birth_hour = profile.birth_time_precision === 'unknown' || profile.birth_hour === '' ? null : Number(profile.birth_hour)
  profile.birth_minute = profile.birth_time_precision === 'unknown' || profile.birth_minute === '' ? null : Number(profile.birth_minute)
  return profile
}
