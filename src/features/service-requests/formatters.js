export const SERVICE_REQUEST_STATUS_LABELS = {
  submitted: '待接单',
  accepted: '待生成初稿',
  ai_processing: 'AI 处理中',
  ai_ready: '待审校',
  reviewing: '审校中',
  needs_info: '待补资料',
  failed: '生成失败',
  delivered: '已交付',
  workflow_complete: '内容审核完成',
  withdrawn: '已撤回',
  rejected: '已拒绝'
}

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

export function topicLabel(topics) {
  const labels = {
    career: '职业发展',
    relationship: '亲密关系',
    family: '家庭议题',
    self: '自我价值',
    growth: '个人成长',
    stress: '压力焦虑'
  }
  return (topics || []).map(topic => labels[topic] || topic).join('、') || '综合自我探索'
}

export function requestGoal(item) {
  return item.service_type === 'calendar'
    ? item.request_preview?.calendar_goal || '—'
    : topicLabel(item.request_preview?.selected_topics)
}

export function formatDate(value) {
  return value ? new Date(value).toLocaleDateString('zh-CN') : '—'
}

export function prettyJson(value) {
  return JSON.stringify(value || {}, null, 2)
}

export function errorText(error) {
  return error.response?.data?.detail || '工作台请求失败，请稍后重试'
}
