import { REPORT_ISSUE_TYPE_LABELS } from '../../utils/displayLabels.js'

export function textDifference(before = '', after = '') {
  let start = 0
  while (start < before.length && start < after.length && before[start] === after[start]) start++
  let oldEnd = before.length, newEnd = after.length
  while (oldEnd > start && newEnd > start && before[oldEnd - 1] === after[newEnd - 1]) { oldEnd--; newEnd-- }
  return { prefix: before.slice(0, start), removed: before.slice(start, oldEnd), added: after.slice(start, newEnd), suffix: before.slice(oldEnd) }
}

const RAW_TYPE_PATTERN = /^[A-Za-z0-9_.:-]+$/

export function reviewIssueHeadline(issue) {
  const type = issue.type || ''
  if (REPORT_ISSUE_TYPE_LABELS[type]) return REPORT_ISSUE_TYPE_LABELS[type]
  const label = reviewIssueLabel(issue)
  if (!type) return label
  if (label !== (issue.message || '')) return label
  // 类型本身就是可读分类时用它做标题；纯代码或英文键回退到完整结论，避免泄漏内部标识。
  return RAW_TYPE_PATTERN.test(type) ? label : type
}

export function reviewIssueLabel(issue) {
  const labels = { node_output_required: '等待完整成果生成', node_coverage_missing: '分析覆盖缺失', node_core_review_required: '请完成命理核心核对', birth_time_confirmation_required: '请确认出生时间口径', node_fragment_stale: '相关依据已变化，请修订后重检', node_reference_stale: '引用版本需要核对', node_command_idempotency_conflict: '请求已用于另一个版本，请重试' }
  const core = { birth_time: '出生时间', hour_pillar: '时柱或未知时辰限制', pattern_and_useful_gods: '格局与喜忌' }
  return `${labels[issue.type] || issue.message || issue.type}${core[issue.message] ? `：${core[issue.message]}` : ''}`
}
