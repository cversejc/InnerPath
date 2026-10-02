export const RUN_STATUS_LABELS = {
  PENDING: '排队中',
  RUNNING: '执行中',
  COMPLETED: '已完成',
  FAILED: '失败'
}

export const VERSION_STATUS_LABELS = {
  DRAFT: '草稿',
  EVALUATION: '评测中',
  PUBLISHED: '已发布',
  RETIRED: '已停用'
}

export function parseSpecification(text) {
  try {
    const value = JSON.parse(text)
    if (!value || Array.isArray(value) || typeof value !== 'object') {
      return { value: null, error: 'Skill 配置必须是 JSON 对象。' }
    }
    return { value, error: '' }
  } catch (error) {
    return { value: null, error: `JSON 格式错误：${error.message}` }
  }
}

export function formatTrace(trace = {}) {
  return [
    ['Provider', trace.provider],
    ['Model', trace.model],
    ['输入 Tokens', trace.input_tokens],
    ['输出 Tokens', trace.output_tokens],
    ['估算成本', trace.estimated_cost],
    ['耗时', Number.isFinite(trace.latency_ms) ? `${trace.latency_ms} ms` : null],
    ['完成原因', trace.finish_reason],
    ['策略版本', trace.global_policy_version],
    ['Prompt 摘要', trace.prompt_sha256]
  ].filter(([, value]) => value !== null && value !== undefined && value !== '')
}

export function sampleInput() {
  return {
    profile: {
      name: '测试用户',
      gender: 'female',
      birth_year: 1992,
      birth_month: 6,
      birth_day: 18,
      birth_hour: 9,
      birth_minute: 30,
      calendar_type: 'solar',
      birth_time_precision: 'exact'
    },
    context: {
      focus_topics: ['career', 'growth'],
      current_challenge: '正在评估职业方向，希望看清适合先验证的下一步。',
      expected_outcomes: ['方向指引', '解决方案'],
      additional_info: '近期在评估职业方向，希望看清适合先验证的下一步。'
    }
  }
}
