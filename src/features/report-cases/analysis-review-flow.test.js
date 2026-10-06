import assert from 'node:assert/strict'
import test from 'node:test'
import { buildAnalysisDirections, createFragmentReview, fragmentReviewProblem } from './analysis-review-flow.js'

const finding = (key, extra = {}) => ({ finding_key: key, claim: `需要审核的${key}判断`, evidence_refs: ['chart'], relation_refs: [], ...extra })
const fragment = (key, refs) => ({ fragment_key: key, title: `1.1.1 ${key === 'analysis.s1.day_master' ? '日主' : '格局'}`, content: '需要由咨询师核对的分析正文。', finding_refs: refs, evidence_refs: ['chart'] })
const evidence = [{ evidence_key: 'chart', status: 'ACTIVE' }]

test('directions use explicit many-to-many links and include dependencies before actions and unlinked findings', () => {
  const run = { id: 1, input_snapshot: { analysis_context: { sop_contract: { topics: [
    { fragment_key: 'analysis.s1.day_master' }, { fragment_key: 'analysis.s1.structure' }
  ] } } }, output_parsed: {
    findings: [finding('resource'), finding('block'), finding('action', { structured_data: { block_refs: ['block'], reasoning_path: { resource_refs: ['resource'] } } }), finding('unlinked')],
    analysis_fragments: [fragment('analysis.s1.structure', ['resource']), fragment('analysis.s1.day_master', ['action', 'resource'])]
  } }
  const groups = buildAnalysisDirections(run, { findings: [], fragments: [] }, 10)
  assert.equal(groups[0].title, '日主')
  assert.deepEqual(groups[0].findings.map(item => item.key), ['block', 'resource', 'action'])
  assert.deepEqual(groups[1].findings.map(item => item.key), ['resource'])
  assert.deepEqual(groups[2].findings.map(item => item.key), ['unlinked'])
})

test('only persisted decisions count, and newer candidates are not implicitly approved by an older run', () => {
  const run = { id: 2, output_parsed: { findings: [finding('shared', { status: 'CONFIRMED' })],
    analysis_fragments: [fragment('analysis.s1.day_master', ['shared']), fragment('analysis.s1.structure', ['shared'])] } }
  const content = { findings: [finding('shared', { status: 'CONFIRMED', source_skill_run_id: 1, owner_step_task_id: 10 })],
    fragments: [{ fragment_key: 'analysis.s1.day_master', status: 'CONFIRMED', source_skill_run_id: 1 }] }
  let groups = buildAnalysisDirections(run, content, 10)
  assert.equal(groups[0].complete, false)
  assert.equal(groups[0].findings[0].done, false)
  content.findings[0].source_skill_run_id = 2
  groups = buildAnalysisDirections(run, content, 10)
  assert.ok(groups.slice(0, 2).every(group => group.findings[0].done))
  assert.ok(groups.slice(0, 2).every(group => !group.complete))
})

test('upstream sources stay read-only and orphaned or cyclic dependencies are not dropped', () => {
  const run = { id: 3, output_parsed: { findings: [finding('a', { relation_refs: [{ finding_key: 'b' }] }), finding('b', { relation_refs: [{ finding_key: 'a' }] })],
    analysis_fragments: [fragment('analysis.s1.day_master', ['upstream', 'missing'])] } }
  const groups = buildAnalysisDirections(run, { fragments: [], findings: [finding('upstream', { status: 'CONFIRMED', owner_step_task_id: 8 })] }, 10)
  assert.equal(groups[0].findings[0].editable, false)
  assert.equal(groups[0].findings[0].done, true)
  assert.equal(groups[0].findings[1].done, false)
  assert.deepEqual(groups[1].findings.map(item => item.key), ['b', 'a'])
})

test('persisted consultant edits and removed references remain authoritative after a refresh', () => {
  const run = { id: 4, output_parsed: { findings: [finding('rejected')], analysis_fragments: [fragment('analysis.s1.day_master', ['rejected'])] } }
  const current = { fragment_key: 'analysis.s1.day_master', revision_no: 5, source_skill_run_id: 4, status: 'CONFIRMED', content: '咨询师修订后的解释与边界。',
    source_snapshot: { findings: [], evidence: [{ evidence_key: 'chart' }] } }
  const content = { evidence, fragments: [current], findings: [finding('rejected', { status: 'REJECTED', source_skill_run_id: 4, owner_step_task_id: 10 })] }
  const groups = buildAnalysisDirections(run, content, 10)
  assert.equal(groups[0].complete, true)
  assert.equal(groups[0].findings.length, 0)
  assert.equal(groups[1].complete, true)
  const draft = createFragmentReview(groups[0], run.id)
  assert.equal(draft.content, current.content)
  assert.equal(draft.expected_revision_no, 5)
  assert.deepEqual(draft.finding_refs, [])
})

test('analysis confirmation supports multiple sources but blocks rejected findings, stale evidence and mismatched quotes', () => {
  const draft = { content: '原样摘句在这里。', finding_refs: ['one', 'two'], evidence_refs: ['chart'], framework_coverage: { quote: '原样摘句' } }
  const content = { evidence, findings: [finding('one', { status: 'CONFIRMED' }), finding('two', { status: 'REJECTED' })] }
  assert.match(fragmentReviewProblem(draft, content), /判断尚未全部确认/)
  draft.finding_refs = ['one']
  assert.equal(fragmentReviewProblem(draft, content), '')
  draft.finding_refs = []
  assert.equal(fragmentReviewProblem(draft, content), '')
  draft.evidence_refs = []
  assert.match(fragmentReviewProblem(draft, content), /至少保留/)
  draft.evidence_refs = ['chart']
  draft.framework_coverage.quote = '不在正文'
  assert.match(fragmentReviewProblem(draft, content), /逐字出现在当前正文/)
})
