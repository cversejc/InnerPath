export const assessmentTopics = [
  { id: 'career', title: '事业发展', desc: '职业选择、转型与瓶颈突破' },
  { id: 'relationship', title: '感情关系', desc: '恋爱、婚姻与关系模式' },
  { id: 'family', title: '家庭议题', desc: '原生家庭、亲子与家庭沟通' },
  { id: 'finance', title: '财务规划', desc: '经济安排与资源分配' },
  { id: 'health', title: '身心健康', desc: '压力、情绪与身心节奏' },
  { id: 'social', title: '人际关系', desc: '社交圈、朋友与边界' },
  { id: 'self', title: '个人成长', desc: '自我实现与认知提升' },
  { id: 'children', title: '子女教育', desc: '陪伴、沟通与成长支持' },
  { id: 'other', title: '其他', desc: '你想带入说明书的主题' }
]

export const expectedOutcomeOptions = [
  { value: '认识自己', label: '更清晰地认识自己' },
  { value: '解决方案', label: '找到当前问题的解决方案' },
  { value: '方向指引', label: '获得对未来方向的指引' },
  { value: '验证判断', label: '验证自己已有的判断' },
  { value: '心理支持', label: '获得心理上的安慰与支持' },
  { value: '节奏参考', label: '了解自己的命理 / 运势节奏' },
  { value: '其他', label: '其他' }
]

export const decisionStyleOptions = [
  { value: 'intuition', label: '凭直觉判断' },
  { value: 'rational', label: '理性分析利弊' },
  { value: 'family_friends', label: '咨询家人 / 朋友意见' },
  { value: 'professional', label: '寻求专业人士建议' },
  { value: 'wait', label: '顺其自然，等时间给答案' },
  { value: 'other', label: '其他' }
]

export function createEmptyAssessmentContext() {
  return {
    focus_topics: [],
    current_challenge: '',
    expected_outcomes: [],
    issue_duration: '',
    impact_level: '',
    decision_status: '',
    decision_description: '',
    decision_style: [],
    additional_info: ''
  }
}

export function validateAssessmentProfile(profile, currentYear = new Date().getFullYear()) {
  const errors = {}
  if (!String(profile.name || '').trim()) errors.name = '请填写称呼。'
  if (!profile.gender) errors.gender = '请选择性别。'
  if (!profile.calendar_type) errors.calendar_type = '请选择历法类型。'

  const year = Number(profile.birth_year)
  const month = Number(profile.birth_month)
  const day = Number(profile.birth_day)
  if (!year || year < 1900 || year > currentYear) errors.birth_date = '请填写有效的出生日期。'
  else if (!month || month < 1 || month > 12 || !day || day < 1 || day > 31) errors.birth_date = '请填写完整的出生日期。'
  else if (profile.calendar_type === 'solar') {
    if (profile.birth_is_leap_month) errors.birth_date = '公历日期不能选择闰月。'
    const date = new Date(year, month - 1, day)
    if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) errors.birth_date = '公历出生日期不存在，请检查日期。'
  } else if (day > 30) errors.birth_date = '农历日期的日期不能超过 30。'

  if (!['unknown', 'approximate', 'exact'].includes(profile.birth_time_precision)) {
    errors.birth_time_precision = '请选择出生时间准确度。'
  }
  if (profile.birth_time_precision !== 'unknown') {
    if (profile.birth_hour === null || profile.birth_hour === '' || profile.birth_hour === undefined || profile.birth_minute === null || profile.birth_minute === '' || profile.birth_minute === undefined) {
      errors.birth_time = '请选择完整的出生小时和分钟。'
    } else if (Number(profile.birth_hour) > 23 || Number(profile.birth_minute) > 59) {
      errors.birth_time = '出生时间范围不正确。'
    }
  }

  return errors
}

export function validateAssessmentContext(context) {
  const errors = {}
  if (!context.focus_topics.length) errors.focus_topics = '至少选择一个关注领域。'
  if (!String(context.current_challenge || '').trim()) errors.current_challenge = '请描述当前困惑或挑战。'
  if (!context.expected_outcomes.length) errors.expected_outcomes = '至少选择一个期望获得的结果。'
  return errors
}
