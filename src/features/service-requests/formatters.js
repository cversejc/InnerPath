import { formatDate, formatDateTime } from '../../utils/dateTime.js'
import {
  CONSULTATION_TYPE_LABELS,
  SERVICE_REQUEST_STATUS_LABELS,
  topicLabel as formatTopicLabel
} from '../../utils/displayLabels.js'

export { formatDate, formatDateTime, SERVICE_REQUEST_STATUS_LABELS }

export function birthSummary(workspace) {
  const profile = workspace?.request?.request_payload?.profile || {}
  const user = workspace?.user || {}
  const year = user.birth_year || profile.birth_year
  const month = user.birth_month || profile.birth_month
  const day = user.birth_day || profile.birth_day
  if (!year || !month || !day) return '—'
  const calendarType = profile.calendar_type === 'lunar' ? '农历' : '公历'
  const birthTime = profile.birth_hour !== null && profile.birth_hour !== undefined
    ? ` · ${profile.birth_hour}:${String(profile.birth_minute || 0).padStart(2, '0')}`
    : ''
  const monthLabel = profile.birth_is_leap_month ? `闰${month}月` : `${month}月`
  return `${year} 年 ${monthLabel} ${day} 日 · ${calendarType}${birthTime}`
}

export function genderLabel(gender) {
  return { male: '男', female: '女' }[gender] || '—'
}

export function consultationTypeLabel(type) {
  return CONSULTATION_TYPE_LABELS[type] || '方向待确认'
}

export function topicLabel(topics) {
  if (!Array.isArray(topics) || !topics.length) return '综合自我探索'
  return formatTopicLabel(topics, '其他关注主题')
}

export function requestGoal(item) {
  return item.service_type === 'calendar'
    ? item.request_preview?.calendar_goal || '—'
    : topicLabel(item.request_preview?.selected_topics)
}

export function prettyJson(value) {
  return JSON.stringify(value || {}, null, 2)
}

export function errorText(error) {
  return error.response?.data?.detail || '工作台请求失败，请稍后重试'
}
