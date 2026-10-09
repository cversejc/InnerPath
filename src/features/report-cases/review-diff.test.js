import { test } from 'node:test'
import assert from 'node:assert/strict'
import { textDifference, reviewIssueHeadline, reviewIssueLabel } from './review-diff.js'

test('shows the edited span without losing unchanged human text', () => {
  assert.deepEqual(textDifference('人工修改。原句。结尾', '人工修改。新句。结尾'), { prefix: '人工修改。', removed: '原', added: '新', suffix: '句。结尾' })
  const value = textDifference('重复内容', '重复内容')
  assert.equal(value.removed, '')
  assert.equal(value.added, '')
})
test('core review blockers name the actual required check', () => {
  assert.match(reviewIssueLabel({ type: 'node_core_review_required', message: 'hour_pillar' }), /未知时辰/)
})
test('issue headline keeps the type when the message already carries the detail', () => {
  const issue = { type: '事实一致性', message: '正文与结构化事实不一致，需核对大运十神标注。' }
  assert.equal(reviewIssueHeadline(issue), '事实一致性')
  assert.equal(reviewIssueLabel(issue), issue.message)
  assert.equal(reviewIssueHeadline({ type: 'node_output_required', message: '生成完整成果后再检查' }), '等待完整成果生成')
})
test('issue headline translates quality codes and never leaks raw keys', () => {
  assert.equal(reviewIssueHeadline({ type: 'FINDING_OVER_REPEATED', message: 'Finding S4.B01 在 9 个报告片段中重复出现' }), '同一专业判断被多段引用')
  assert.equal(reviewIssueHeadline({ type: 'UNKNOWN_INTERNAL_CODE', message: '内部校验未通过' }), '内部校验未通过')
})
