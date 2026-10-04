import test from 'node:test'
import assert from 'node:assert/strict'
import { feedbackPreviewFromRun, formatTrace, isReportAnalysisFeedbackRun, isReportSkillFeedbackRun, parseSpecification, sampleInput } from './studio.js'

test('specification editor reports malformed and non-object JSON', () => {
  assert.match(parseSpecification('{').error, /JSON 格式错误/)
  assert.match(parseSpecification('[]').error, /JSON 对象/)
  assert.deepEqual(parseSpecification('{"identity":{}}'), {
    value: { identity: {} },
    error: ''
  })
})

test('trace view omits absent fields and includes provider metadata', () => {
  assert.deepEqual(formatTrace({ provider: 'deepseek', latency_ms: 23 }), [
    ['模型服务', 'deepseek'],
    ['耗时', '23 ms']
  ])
})

test('debug sample contains profile and application context', () => {
  const sample = sampleInput()
  assert.equal(sample.profile.birth_year, 1992)
  assert.deepEqual(sample.context.focus_topics, ['career', 'growth'])
})

test('consultant feedback preview reuses the node input and feedback without changing the report', () => {
  const run = {
    id: 41,
    report_case_id: 12,
    target_type: 'REPORT_ANALYSIS_DRAFT',
    runtime_instruction: '请区分事实与推断。',
    input_snapshot: { profile: { birth_year: 1991 }, analysis_context: { step_key: 'S2' } }
  }

  assert.equal(isReportAnalysisFeedbackRun(run), true)
  assert.deepEqual(feedbackPreviewFromRun(run), {
    inputText: JSON.stringify(run.input_snapshot, null, 2),
    runtimeInstruction: '请区分事实与推断。'
  })
  assert.equal(isReportAnalysisFeedbackRun({ ...run, runtime_instruction: '' }), false)
  assert.equal(isReportAnalysisFeedbackRun({ ...run, report_case_id: null }), false)
})

test('authoring and final-check feedback runs can be routed into the skill editor with their actual inputs', () => {
  const sourceRuns = [
    {
      id: 52,
      report_case_id: 12,
      target_type: 'NARRATIVE_CANDIDATES',
      target_key: 'S5',
      runtime_instruction: '请让主线更贴近用户确认的矛盾。',
      input_snapshot: { context: { semantic_model: { findings: ['confirmed'] } } }
    },
    {
      id: 53,
      report_case_id: 12,
      target_type: 'REPORT_FRAGMENT',
      target_key: 'report.identity',
      runtime_instruction: '减少重复解释。',
      input_snapshot: { context: { fragment_request: { fragment_key: 'report.identity' } } }
    },
    {
      id: 54,
      report_case_id: 12,
      target_type: 'REPORT_QA',
      target_key: 'report.final',
      runtime_instruction: '重新检查事实与假设边界。',
      input_snapshot: { context: { qa_input: { report_fragments: ['confirmed copy'] } } }
    }
  ]

  for (const run of sourceRuns) {
    assert.equal(isReportSkillFeedbackRun(run), true)
    assert.deepEqual(feedbackPreviewFromRun(run), {
      inputText: JSON.stringify(run.input_snapshot, null, 2),
      runtimeInstruction: run.runtime_instruction
    })
  }
  assert.equal(isReportAnalysisFeedbackRun(sourceRuns[0]), false)
  assert.equal(isReportSkillFeedbackRun({ ...sourceRuns[0], runtime_instruction: '' }), false)
  assert.equal(isReportSkillFeedbackRun({ ...sourceRuns[0], target_type: 'REPORT_COHERENCE' }), false)
})
