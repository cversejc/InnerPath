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
