import assert from 'node:assert/strict'
import test from 'node:test'
import { reactive } from 'vue'
import apiClient from '../../../utils/apiClient.js'
import methods from './report-case.js'
import simpleReportCaseMethods from './simple-report-case.js'
import reportReviewMethods from './report-review.js'

test('a simplified case loads only the case and its simple versions', async t => {
  const previousAdapter = apiClient.defaults.adapter
  const previousStorage = Object.getOwnPropertyDescriptor(globalThis, 'sessionStorage')
  Object.defineProperty(globalThis, 'sessionStorage', { configurable: true, value: { getItem: () => null } })
  t.after(() => {
    apiClient.defaults.adapter = previousAdapter
    if (previousStorage) Object.defineProperty(globalThis, 'sessionStorage', previousStorage)
    else delete globalThis.sessionStorage
  })

  const urls = []
  apiClient.defaults.adapter = async config => {
    urls.push(config.url)
    const data = config.url === '/report-cases/41'
      ? {
          id: 41,
          status: 'ACTIVE',
          application_snapshot: { workflow_key: 'report.simple' },
          workflow_instance: {
            steps: [
              { id: 1, step_key: 'S1', sequence_no: 1, status: 'READY', config_snapshot: { output_version: 1 } },
              { id: 2, step_key: 'S2', sequence_no: 2, status: 'PENDING', config_snapshot: { output_version: 2 } },
              { id: 3, step_key: 'S3', sequence_no: 3, status: 'PENDING', config_snapshot: { output_version: 3 } },
              { id: 4, step_key: 'S4', sequence_no: 4, status: 'PENDING', config_snapshot: { output_version: 4 } },
              { id: 5, step_key: 'S5', sequence_no: 5, status: 'PENDING', config_snapshot: { output_version: 5 } },
              { id: 6, step_key: 'S6', sequence_no: 6, status: 'PENDING', config_snapshot: { output_version: 6, final_gate: true } }
            ]
          }
        }
      : { items: [] }
    return { data, status: 200, statusText: 'OK', headers: {}, config }
  }

  const context = {
    ...simpleReportCaseMethods,
    reportCaseLoading: false,
    reportCase: null,
    workspace: null,
    selectedRequest: null,
    selectedReportStepKey: '',
    simpleReportLoading: false,
    simpleReportSaving: false,
    simpleReportVersions: [],
    simpleReportDraft: null,
    currentReportStep: null,
    $route: { query: {} },
    syncWorkspaceRoute() {},
    scrollWorkspaceToTop() {},
    errorText: error => { throw error }
  }

  await methods.loadReportCaseData.call(context, 41)

  assert.deepEqual(urls, ['/report-cases/41', '/report-cases/41/simple/versions'])
  assert.equal(context.reportCase.id, 41)
  assert.equal(context.simpleReportLoading, false)
})

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

function importableCase(overrides = {}) {
  return {
    id: 81,
    status: 'ACTIVE',
    review_policy_version: 'six-node-review-v1',
    workflow_instance: {
      steps: ['S1', 'S2', 'S3', 'S4', 'S5', 'S6'].map(step_key => ({
        step_key,
        status: step_key === 'S6' ? 'READY' : 'PENDING'
      }))
    },
    ...overrides
  }
}

function importContext(overrides = {}) {
  return {
    reportCase: importableCase(),
    reportImportDialog: {
      visible: true,
      title: '',
      sourceFilename: '',
      content: '',
      error: '',
      saving: false,
      idempotencyKey: 'import-key-1'
    },
    errorText: error => error.message,
    loadReportCaseData: async () => {},
    selectReportNode: () => {},
    ...overrides
  }
}

function stubSessionStorage(t) {
  const previous = Object.getOwnPropertyDescriptor(globalThis, 'sessionStorage')
  Object.defineProperty(globalThis, 'sessionStorage', { configurable: true, value: { getItem: () => null } })
  t.after(() => {
    if (previous) Object.defineProperty(globalThis, 'sessionStorage', previous)
    else delete globalThis.sessionStorage
  })
}

test('report import is offered only while S1-S5 are untouched under the six-node policy', () => {
  assert.equal(methods.canImportReportCase.call(importContext()), true)
  assert.equal(methods.canImportReportCase.call(importContext({
    reportCase: importableCase({ review_policy_version: 'import-review-v1' })
  })), false)
  assert.equal(methods.canImportReportCase.call(importContext({
    reportCase: importableCase({ status: 'DELIVERED' })
  })), false)
  const started = importableCase()
  started.workflow_instance.steps[2].status = 'COMPLETED'
  assert.equal(methods.canImportReportCase.call(importContext({ reportCase: started })), false)
  const importable = importableCase()
  importable.workflow_instance.steps[1].status = 'IN_REVIEW'
  assert.equal(methods.canImportReportCase.call(importContext({ reportCase: importable })), false)
})

test('submitting an imported report posts the digest and switches the workspace to S6', async t => {
  stubSessionStorage(t)
  const previousAdapter = apiClient.defaults.adapter
  t.after(() => { apiClient.defaults.adapter = previousAdapter })
  const requests = []
  apiClient.defaults.adapter = async config => {
    requests.push({ url: config.url, data: JSON.parse(config.data) })
    return {
      data: { id: 81, review_policy_version: 'import-review-v1' },
      status: 200,
      statusText: 'OK',
      headers: {},
      config
    }
  }
  let loaded, selected
  const context = importContext({
    reportImportDialog: {
      visible: true,
      title: '  快速报告  ',
      sourceFilename: '',
      content: '  # 你是谁\n甲方\n\n# 卡在哪\n乙方\n\n# 往哪去\n丙方  ',
      error: '',
      saving: false,
      idempotencyKey: 'import-key-1'
    },
    loadReportCaseData: async caseId => { loaded = caseId },
    selectReportNode: key => { selected = key }
  })
  await methods.submitReportImport.call(context)
  assert.equal(requests.length, 1)
  assert.equal(requests[0].url, '/report-cases/81/import-report')
  assert.match(requests[0].data.content_sha256, /^[0-9a-f]{64}$/)
  assert.equal(requests[0].data.idempotency_key, 'import-key-1')
  assert.equal(requests[0].data.title, '快速报告')
  assert.equal(requests[0].data.source_filename, null)
  assert.equal(requests[0].data.content.startsWith('# 你是谁'), true)
  assert.equal(loaded, 81)
  assert.equal(selected, 'S6')
  assert.equal(context.reportImportDialog.visible, false)
  assert.equal(context.reportImportDialog.saving, false)
  assert.equal(context.message.includes('第 6 步'), true)
})

test('a failed import keeps the draft and rotates the idempotency key', async t => {
  stubSessionStorage(t)
  const previousAdapter = apiClient.defaults.adapter
  t.after(() => { apiClient.defaults.adapter = previousAdapter })
  apiClient.defaults.adapter = async config => {
    const error = new Error('Request failed with status code 409')
    error.config = config
    error.response = { status: 409, data: { detail: 'report_import_duplicate_content' }, headers: {}, config }
    throw error
  }
  const context = importContext({
    reportImportDialog: {
      visible: true,
      title: '',
      sourceFilename: 'draft.md',
      content: '# 你是谁\n甲方\n\n# 卡在哪\n乙方\n\n# 往哪去\n丙方',
      error: '',
      saving: false,
      idempotencyKey: 'import-key-1'
    }
  })
  await methods.submitReportImport.call(context)
  assert.equal(context.reportImportDialog.idempotencyKey !== 'import-key-1', true)
  assert.equal(context.reportImportDialog.error, '同一份报告已被导入到另一份申请，请确认是否选错了申请。')
  assert.equal(context.reportImportDialog.visible, true)
  assert.equal(context.reportImportDialog.saving, false)
  assert.equal(context.reportImportDialog.sourceFilename, 'draft.md')
})

test('a rejected model normalization surfaces the normalization failure message', async t => {
  stubSessionStorage(t)
  const previousAdapter = apiClient.defaults.adapter
  t.after(() => { apiClient.defaults.adapter = previousAdapter })
  apiClient.defaults.adapter = async config => {
    const error = new Error('Request failed with status code 422')
    error.config = config
    error.response = { status: 422, data: { detail: 'report_import_normalization_failed' }, headers: {}, config }
    throw error
  }
  const context = importContext({
    reportImportDialog: {
      visible: true,
      title: '',
      sourceFilename: '',
      content: '这是一份没有三段标题的原始报告。',
      error: '',
      saving: false,
      idempotencyKey: 'import-key-1'
    }
  })
  await methods.submitReportImport.call(context)
  assert.equal(context.reportImportDialog.error, '系统暂时无法整理报告结构，请检查正文后重试。')
  assert.equal(context.reportImportDialog.visible, true)
  assert.equal(context.reportImportDialog.saving, false)
})

function finalGateContext(overrides = {}) {
  return {
    reportCase: { id: 81, review_policy_version: 'import-review-v1' },
    reportStepSaving: false,
    reportQuality: {
      advisory_only: true,
      can_finalize: true,
      can_approve: false,
      unresolved_advisories: [{ id: 1 }, { id: 2 }]
    },
    finalGateNote: '',
    confirmAction: async () => true,
    loadReportCaseData: async () => {},
    errorText: error => error.message,
    ...overrides
  }
}

test('advisory final gate approval works without a completed check and sends the note', async t => {
  stubSessionStorage(t)
  const previousAdapter = apiClient.defaults.adapter
  t.after(() => { apiClient.defaults.adapter = previousAdapter })
  const requests = []
  apiClient.defaults.adapter = async config => {
    requests.push({ url: config.url, data: JSON.parse(config.data) })
    return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
  }
  let loaded, confirmMessage
  const context = finalGateContext({
    finalGateNote: '  保留建议：用户未提供出生时间，已在报告中说明。  ',
    confirmAction: async options => { confirmMessage = options.message; return true },
    loadReportCaseData: async caseId => { loaded = caseId }
  })
  await methods.approveReportFinalGate.call(context)
  assert.equal(requests.length, 1)
  assert.equal(requests[0].url, '/report-cases/81/final-gate/approve')
  assert.equal(requests[0].data.attested, true)
  assert.equal(requests[0].data.note, '保留建议：用户未提供出生时间，已在报告中说明。')
  assert.equal(confirmMessage.includes('2 条未处理建议'), true)
  assert.equal(context.finalGateNote, '')
  assert.equal(loaded, 81)
  assert.equal(context.message, '最终复核已通过，可以生成交付版本。')
})

test('final gate approval sends a null note when the consultant leaves it empty', async t => {
  stubSessionStorage(t)
  const previousAdapter = apiClient.defaults.adapter
  t.after(() => { apiClient.defaults.adapter = previousAdapter })
  const requests = []
  apiClient.defaults.adapter = async config => {
    requests.push({ url: config.url, data: JSON.parse(config.data) })
    return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
  }
  const context = finalGateContext({
    reportCase: { id: 81, review_policy_version: 'six-node-review-v1' },
    reportQuality: { advisory_only: false, can_finalize: true, can_approve: true, unresolved_advisories: [] },
    finalGateNote: '   '
  })
  await methods.approveReportFinalGate.call(context)
  assert.equal(requests[0].data.note, null)
})

test('final gate approval stops before the request while revised report fragments are unconfirmed', async t => {
  stubSessionStorage(t)
  const previousAdapter = apiClient.defaults.adapter
  t.after(() => { apiClient.defaults.adapter = previousAdapter })
  let requests = 0
  apiClient.defaults.adapter = async config => {
    requests += 1
    return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
  }
  const context = finalGateContext({
    reportCaseContent: {
      fragments: [
        { fragment_type: 'REPORT', fragment_key: 'report.intro', status: 'PROPOSED' },
        { fragment_type: 'REPORT', fragment_key: 'report.body', status: 'CONFIRMED' }
      ]
    }
  })
  await methods.approveReportFinalGate.call(context)
  assert.equal(requests, 0)
  assert.equal(context.message.includes('修改后稿件'), true)
  assert.equal(context.message.includes('1 段'), true)
})

test('confirming the manuscript confirms every unconfirmed report fragment as a style edit', async t => {
  stubSessionStorage(t)
  const previousAdapter = apiClient.defaults.adapter
  t.after(() => { apiClient.defaults.adapter = previousAdapter })
  const requests = []
  apiClient.defaults.adapter = async config => {
    requests.push({ url: config.url, data: JSON.parse(config.data) })
    return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
  }
  let loaded, confirmMessage
  const context = {
    reportCase: { id: 81 },
    selectedReportStepKey: 'S6',
    canEditSelectedReportStep: true,
    reportFragmentSaving: false,
    reportCaseContent: {
      fragments: [
        {
          fragment_key: 'report.intro',
          fragment_type: 'REPORT',
          revision_no: 3,
          title: '开篇',
          content: '修订后的开篇',
          status: 'PROPOSED',
          source_snapshot: { findings: [{ finding_key: 's1.f1' }], fragments: [], evidence: [{ evidence_key: 'e1' }] }
        },
        { fragment_key: 'report.body', fragment_type: 'REPORT', revision_no: 1, status: 'CONFIRMED' },
        { fragment_key: 'analysis.s3.a', fragment_type: 'ANALYSIS', revision_no: 1, status: 'PROPOSED' }
      ]
    },
    confirmAction: async options => { confirmMessage = options.message; return true },
    loadReportCaseData: async caseId => { loaded = caseId },
    errorText: error => error.message
  }
  await reportReviewMethods.confirmReportManuscript.call(context)
  assert.equal(requests.length, 1)
  assert.equal(requests[0].url, '/report-cases/81/steps/S6/fragments/report.intro')
  assert.equal(requests[0].data.status, 'CONFIRMED')
  assert.equal(requests[0].data.edit_kind, 'STYLE')
  assert.equal(requests[0].data.expected_revision_no, 3)
  assert.equal(requests[0].data.title, '开篇')
  assert.equal(requests[0].data.content, '修订后的开篇')
  assert.deepEqual(requests[0].data.finding_refs, ['s1.f1'])
  assert.deepEqual(requests[0].data.evidence_refs, ['e1'])
  assert.equal(confirmMessage.includes('1 段'), true)
  assert.equal(loaded, 81)
  assert.equal(context.reportFragmentSaving, false)
  assert.equal(context.message, '修改后的稿件已确认，可以完成最终复核并生成交付版本。')
})

test('confirming the manuscript refuses to confirm while a report fragment is stale', async t => {
  stubSessionStorage(t)
  const previousAdapter = apiClient.defaults.adapter
  t.after(() => { apiClient.defaults.adapter = previousAdapter })
  let requests = 0
  apiClient.defaults.adapter = async config => {
    requests += 1
    return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
  }
  const context = {
    reportCase: { id: 81 },
    selectedReportStepKey: 'S6',
    canEditSelectedReportStep: true,
    reportFragmentSaving: false,
    reportCaseContent: {
      fragments: [
        { fragment_key: 'report.intro', fragment_type: 'REPORT', revision_no: 3, status: 'STALE' }
      ]
    },
    confirmAction: async () => true,
    loadReportCaseData: async () => {},
    errorText: error => error.message
  }
  await reportReviewMethods.confirmReportManuscript.call(context)
  assert.equal(requests, 0)
  assert.equal(context.message.includes('来源'), true)
})

test('final gate approval stops while a report fragment source is stale', async t => {
  stubSessionStorage(t)
  const previousAdapter = apiClient.defaults.adapter
  t.after(() => { apiClient.defaults.adapter = previousAdapter })
  let requests = 0
  apiClient.defaults.adapter = async config => {
    requests += 1
    return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
  }
  const context = finalGateContext({
    reportCaseContent: {
      fragments: [
        { fragment_type: 'REPORT', fragment_key: 'report.intro', status: 'STALE' },
        { fragment_type: 'REPORT', fragment_key: 'report.body', status: 'CONFIRMED' }
      ]
    }
  })
  await methods.approveReportFinalGate.call(context)
  assert.equal(requests, 0)
  assert.equal(context.message.includes('来源依据已更新'), true)
  assert.equal(context.message.includes('1 段'), true)
})
