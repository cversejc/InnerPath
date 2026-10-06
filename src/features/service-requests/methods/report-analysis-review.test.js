import assert from 'node:assert/strict'
import test from 'node:test'
import apiClient from '../../../utils/apiClient.js'
import methods from './report-analysis.js'

function setup(t, adapter) {
  const previousAdapter = apiClient.defaults.adapter
  const storage = Object.getOwnPropertyDescriptor(globalThis, 'sessionStorage')
  Object.defineProperty(globalThis, 'sessionStorage', { configurable: true, value: { getItem: () => null } })
  apiClient.defaults.adapter = adapter
  t.after(() => {
    apiClient.defaults.adapter = previousAdapter
    if (storage) Object.defineProperty(globalThis, 'sessionStorage', storage)
    else delete globalThis.sessionStorage
  })
  return { reportCase: { id: 18 }, canEditSelectedReportStep: true, currentReportStep: { step_key: 'S1' },
    reportCaseContent: { findings: [], fragments: [] }, reportAnalysisFindingSavingKey: '', reportAnalysisFragmentSavingKey: '',
    errorText: () => '保存失败，请重试。', confirmAction: async () => true }
}

test('inline review sends one atomic request and refreshes silently without changing the workspace', async t => {
  let request, completed, refreshOptions
  const context = setup(t, async config => {
    request = { url: config.url, data: JSON.parse(config.data) }
    return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
  })
  context.workspaceSection = 'analysis'
  context.loadReportCaseData = async (id, options) => { assert.equal(id, 18); refreshOptions = options }
  const candidate = { finding_key: 's1.day_master' }
  await methods.reviewReportAnalysisCandidate.call(context, { run: { id: 336, output_parsed: { findings: [candidate] } }, kind: 'finding', candidate,
    expectedRevisionNo: null, review: { claim: '咨询师已审核的判断', semantic_role: 'OBSERVATION', status: 'CONFIRMED' }, onComplete: value => { completed = value } })
  assert.equal(request.url, '/report-cases/18/steps/S1/analysis-drafts/336/findings/s1.day_master/apply')
  assert.equal(request.data.finding_review.status, 'CONFIRMED')
  assert.deepEqual(refreshOptions, { silent: true })
  assert.equal(context.workspaceSection, 'analysis')
  assert.equal(context.reportAnalysisFindingSavingKey, '')
  assert.equal(completed.success, true)
})

test('a failed save preserves the review flow and cannot trigger successful advancement', async t => {
  const context = setup(t, async () => { throw { response: { status: 422, data: { detail: 'report_analysis_fragment_findings_unconfirmed' } } } })
  context.loadReportCaseData = async () => { assert.fail('validation failure must retain local edits') }
  let completed
  const candidate = { fragment_key: 'analysis.s1.day_master' }
  await methods.reviewReportAnalysisCandidate.call(context, { run: { id: 336, output_parsed: { analysis_fragments: [candidate] } }, kind: 'fragment', candidate,
    expectedRevisionNo: null, review: { content: '保留在编辑器中的分析', status: 'CONFIRMED' }, onComplete: value => { completed = value } })
  assert.equal(completed.success, false)
  assert.match(completed.message, /判断未确认/)
  assert.equal(context.reportAnalysisFragmentSavingKey, '')
})
