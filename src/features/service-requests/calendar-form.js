export const CALENDAR_TIME_OPTIONS = [
  { value: 'unknown', label: '不知道' },
  { value: 'approximate', label: '大概时间' },
  { value: 'exact', label: '精确时间' }
]

export function localDateKey(date = new Date()) {
  const pad = value => String(value).padStart(2, '0')
  return date.getFullYear() + '-' + pad(date.getMonth() + 1) + '-' + pad(date.getDate())
}

export function addCalendarDays(dateKey, days) {
  const date = new Date(dateKey + 'T12:00:00')
  date.setDate(date.getDate() + days)
  return localDateKey(date)
}

export function createCalendarRequestForm() {
  return {
    name: '',
    gender: '',
    birth_year: null,
    birth_month: null,
    birth_day: null,
    birth_is_leap_month: false,
    birth_hour: null,
    birth_minute: null,
    birth_place: '',
    calendar_type: 'solar',
    time_accuracy: 'unknown',
    start_date: localDateKey(),
    calendar_goal: '',
    additional_info: ''
  }
}

export function validateCalendarRequestForm(form, currentYear = 2026) {
  const errors = {}
  if (!form.name) errors.name = '请填写姓名'
  if (!form.gender) errors.gender = '请选择性别'
  const year = Number(form.birth_year)
  const month = Number(form.birth_month)
  const day = Number(form.birth_day)
  if (!year || !month || !day) {
    errors.birth = '请填写完整出生日期'
  } else if (year < 1900 || year > currentYear || month < 1 || month > 12 || day < 1 || day > 31) {
    errors.birth = '出生日期格式不正确'
  } else if (form.calendar_type === 'solar') {
    if (form.birth_is_leap_month) errors.birth = '公历日期不能选择闰月'
    const value = new Date(year, month - 1, day)
    if (value.getFullYear() !== year || value.getMonth() !== month - 1 || value.getDate() !== day) {
      errors.birth = '出生日期不存在'
    }
  } else if (day > 30) {
    errors.birth = '农历日期不能超过 30 日'
  }
  if (!form.start_date) errors.start_date = '请选择起始日期'
  if (!form.calendar_goal) errors.calendar_goal = '请填写本次关注目标'
  return errors
}

export function buildCalendarRequestPayload(form) {
  return {
    profile: {
      name: form.name,
      gender: form.gender,
      birth_year: Number(form.birth_year),
      birth_month: Number(form.birth_month),
      birth_day: Number(form.birth_day),
      birth_is_leap_month: Boolean(form.calendar_type === 'lunar' && form.birth_is_leap_month),
      birth_hour: form.time_accuracy === 'unknown' ? null : Number(form.birth_hour),
      birth_minute: form.time_accuracy === 'unknown' ? null : Number(form.birth_minute || 0),
      birth_place: form.birth_place || null,
      calendar_type: form.calendar_type,
      time_accuracy: form.time_accuracy
    },
    selected_topics: [],
    calendar_goal: form.calendar_goal,
    start_date: form.start_date,
    additional_info: form.additional_info || null
  }
}
