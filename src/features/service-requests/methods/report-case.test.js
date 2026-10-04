import assert from 'node:assert/strict'
import test from 'node:test'
import { reactive } from 'vue'
import apiClient from '../../../utils/apiClient.js'
import methods from './report-case.js'

test('accepting a reactive finding saves a detached revision instead of failing to clone its proxy', async t => {
  const previousAdapter = apiClient.defaults.adapter
  const previousStorage = Object.getOwnPropertyDescriptor(globalThis, 'sessionStorage')
  Object.defineProperty(globalThis, 'sessionStorage', { configurable: true, value: { getItem: () => null } })
  t.after(() => {
    apiClient.defaults.adapter = previousAdapter
    if (previousStorage) Object.defineProperty(globalThis, 'sessionStorage', previousStorage)
    else delete globalThis.sessionStorage
  })
  let saved, refreshed = false
  apiClient.defaults.adapter = async config => {
    saved = { url: config.url, data: JSON.parse(config.data) }
    return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
  }
  const finding = reactive({ finding_key: 's1.day_master', revision_no: 1, claim: '日主线索须结合用户资料核对', kind: 'FINDING', semantic_role: 'OBSERVATION', confidence: 'MEDIUM', importance: 'HIGH', reportability: 'OPTIONAL', status: 'PROPOSED', evidence_refs: ['foundation'], relation_refs: [{ relation: 'SUPPORTS', finding_key: 'other' }], structured_data_json: { candidate: { verified: false } } })
  const context = { reportCase: { id: 13 }, currentReportStep: { step_key: 'S1' }, reportFindingSaving: false,
    editReportFinding: methods.editReportFinding, saveReportFinding: methods.saveReportFinding,
    loadReportCaseData: async () => { refreshed = true }, errorText: error => { throw error } }
  await methods.setReportFindingStatus.call(context, finding, 'CONFIRMED')
  assert.equal(saved.url, '/report-cases/13/steps/S1/findings/s1.day_master')
  assert.equal(saved.data.status, 'CONFIRMED')
  assert.equal(saved.data.expected_revision_no, 1)
  assert.equal(refreshed, true)
  assert.equal(finding.status, 'PROPOSED')
  context.reportFindingDraft.structured_data.candidate.verified = true
  context.reportFindingDraft.relation_refs[0].relation = 'CONFLICTS'
  assert.equal(finding.structured_data_json.candidate.verified, false)
  assert.equal(finding.relation_refs[0].relation, 'SUPPORTS')
})

test('consultant feedback reruns include the completed S5 or S6 source run', async t => {
  const previousAdapter = apiClient.defaults.adapter
  const previousStorage = Object.getOwnPropertyDescriptor(globalThis, 'sessionStorage')
  Object.defineProperty(globalThis, 'sessionStorage', { configurable: true, value: { getItem: () => null } })
  t.after(() => {
    apiClient.defaults.adapter = previousAdapter
    if (previousStorage) Object.defineProperty(globalThis, 'sessionStorage', previousStorage)
    else delete globalThis.sessionStorage
  })

  const requests = []
  apiClient.defaults.adapter = async config => {
    requests.push({ url: config.url, data: JSON.parse(config.data) })
    return { data: { quality_status: 'PENDING', latest_validator_run: { id: 303, status: 'PENDING' } }, status: 202, statusText: 'Accepted', headers: {}, config }
  }
  let refreshed = 0
  const context = {
    reportCase: { id: 52 },
    currentReportStep: { step_key: 'S5', status: 'IN_REVIEW' },
    reportNarrativeSaving: false,
    narrativeFeedbackDrafts: { 101: '请避免重复解释，突出已确认的判断。' },
    loadReportCaseData: async () => { refreshed += 1 },
    errorText: error => { throw error }
  }
  await methods.rerunNarrativeWithFeedback.call(context, { id: 101, status: 'COMPLETED' })
  assert.equal(requests[0].url, '/report-cases/52/steps/S5/narrative-candidates')
  assert.equal(requests[0].data.source_run_id, 101)
  assert.equal(requests[0].data.runtime_instruction, '请避免重复解释，突出已确认的判断。')
  assert.equal(context.narrativeFeedbackDrafts[101], '')

  context.currentReportStep = { step_key: 'S6', status: 'IN_REVIEW' }
  context.reportQualitySaving = false
  context.reportQuality = { latest_validator_run: { id: 202, status: 'COMPLETED' } }
  context.qualityFeedbackDraft = '请复核报告中的事实与假设边界。'
  context.scheduleNarrativePoll = () => {}
  await methods.runReportQuality.call(context, {
    runtimeInstruction: context.qualityFeedbackDraft,
    sourceRunId: context.reportQuality.latest_validator_run.id
  })
  assert.equal(requests[1].url, '/report-cases/52/quality/run')
  assert.equal(requests[1].data.source_run_id, 202)
  assert.equal(requests[1].data.runtime_instruction, '请复核报告中的事实与假设边界。')
  assert.equal(context.qualityFeedbackDraft, '')
  assert.equal(refreshed, 1)
})
