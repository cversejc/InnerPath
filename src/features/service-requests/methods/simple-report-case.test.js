import assert from 'node:assert/strict'
import test from 'node:test'
import apiClient from '../../../utils/apiClient.js'
import simpleReportCaseMethods from './simple-report-case.js'

const SIMPLE_STEP_KEYS = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6']

function simpleCase() {
  return {
    id: 41,
    status: 'ACTIVE',
    application_snapshot: { workflow_key: 'report.simple' },
    workflow_instance: {
      steps: SIMPLE_STEP_KEYS.map((stepKey, index) => ({
        id: index + 1,
        step_key: stepKey,
        sequence_no: index + 1,
        status: index === 0 ? 'READY' : 'PENDING',
        config_snapshot: {
          output_version: index + 1,
          ...(index === SIMPLE_STEP_KEYS.length - 1 ? { final_gate: true } : {})
        }
      }))
    }
  }
}

function simpleContext(overrides = {}) {
  return {
    ...simpleReportCaseMethods,
    simpleReportLoading: false,
    simpleReportSaving: false,
    simpleReportVersions: [],
    simpleReportDraft: null,
    selectedReportStepKey: '',
    reportReviewBusy: false,
    reportCase: simpleCase(),
    workspace: null,
    selectedRequest: null,
    message: '',
    routeUpdates: [],
    errorText: error => error.message,
    syncWorkspaceRoute: function (...args) { this.routeUpdates.push(args) },
    scrollWorkspaceToTop() {},
    confirmAction: async () => true,
    reportStepLabel: stepKey => stepKey,
    ...overrides
  }
}

async function withAdapter(adapter, run) {
  const previousAdapter = apiClient.defaults.adapter
  const previousStorage = Object.getOwnPropertyDescriptor(globalThis, 'sessionStorage')
  Object.defineProperty(globalThis, 'sessionStorage', { configurable: true, value: { getItem: () => null } })
  apiClient.defaults.adapter = adapter
  try {
    await run()
  } finally {
    apiClient.defaults.adapter = previousAdapter
    if (previousStorage) Object.defineProperty(globalThis, 'sessionStorage', previousStorage)
    else delete globalThis.sessionStorage
  }
}

test('the second round starts from the first full version', async () => {
  await withAdapter(async config => ({
    data: {
      items: [
        { id: 11, version_no: 1, version_label: 'v1.0', source_step_key: 'S1', report_text: '第一版完整报告' },
        { id: 12, version_no: 2, version_label: 'v2.0', source_step_key: 'S2', report_text: '第二版完整报告' }
      ]
    },
    status: 200,
    statusText: 'OK',
    headers: {},
    config
  }), async () => {
    const context = simpleContext({ selectedReportStepKey: 'S2' })
    await context.loadSimpleReportCaseData(41)

    assert.deepEqual(context.simpleReportVersions.map(item => item.version_no), [1, 2])
    assert.equal(context.simpleReportDraft.step_key, 'S2')
    assert.equal(context.simpleReportDraft.report_text, '第一版完整报告')
  })
})

test('reopening a later round re-seeds an empty draft once the versions arrive', async () => {
  await withAdapter(async config => ({
    data: {
      items: [
        { id: 11, version_no: 1, version_label: 'v1.0', source_step_key: 'S1', report_text: '第一版完整报告' }
      ]
    },
    status: 200,
    statusText: 'OK',
    headers: {},
    config
  }), async () => {
    // Route restoration syncs the draft before the version list has loaded, so
    // the round starts with an empty editor; loading must fill it back in.
    const context = simpleContext({ selectedReportStepKey: 'S2' })
    context.syncSimpleReportDraft('S2')
    assert.equal(context.simpleReportDraft.report_text, '')

    await context.loadSimpleReportCaseData(41)

    assert.equal(context.simpleReportDraft.step_key, 'S2')
    assert.equal(context.simpleReportDraft.report_text, '第一版完整报告')
  })
})

test('reloading keeps an in-progress round instead of overwriting it with the upstream version', async () => {
  await withAdapter(async config => ({
    data: {
      items: [
        { id: 11, version_no: 1, version_label: 'v1.0', source_step_key: 'S1', report_text: '第一版完整报告' }
      ]
    },
    status: 200,
    statusText: 'OK',
    headers: {},
    config
  }), async () => {
    const context = simpleContext({
      selectedReportStepKey: 'S2',
      simpleReportDraft: {
        step_key: 'S2',
        report_text: 'consultant in-progress revision',
        review_note: 'still writing',
        final_gate_confirmed: false
      }
    })

    await context.loadSimpleReportCaseData(41)

    assert.equal(context.simpleReportDraft.report_text, 'consultant in-progress revision')
    assert.equal(context.simpleReportDraft.review_note, 'still writing')
  })
})

test('completing a round advances to the next node seeded with the saved version', async () => {
  const requests = []
  await withAdapter(async config => {
    requests.push({ url: config.url, data: config.data ? JSON.parse(config.data) : null })
    return {
      data: { version: { version_no: 1, version_label: 'v1.0' }, delivered: false, report_id: null },
      status: 200,
      statusText: 'OK',
      headers: {},
      config
    }
  }, async () => {
    const context = simpleContext({
      selectedReportStepKey: 'S1',
      selectedRequest: { id: 41 },
      currentReportStep: simpleCase().workflow_instance.steps[0],
      simpleReportVersions: [],
      simpleReportDraft: {
        step_key: 'S1',
        report_text: '刚刚提交的第一版',
        review_note: '',
        final_gate_confirmed: false
      },
      async loadReportCaseData() {
        this.reportCase.workflow_instance.steps[0].status = 'COMPLETED'
        this.reportCase.workflow_instance.steps[1].status = 'READY'
        this.simpleReportVersions = [
          { id: 11, version_no: 1, version_label: 'v1.0', source_step_key: 'S1', report_text: '刚刚提交的第一版' }
        ]
      }
    })

    await context.completeSimpleReportStep()

    assert.equal(requests.length, 1)
    assert.equal(requests[0].url, '/report-cases/41/simple/steps/S1/complete')
    assert.deepEqual(requests[0].data, {
      report_text: '刚刚提交的第一版',
      review_note: null,
      final_gate_confirmed: false
    })
    assert.equal(context.selectedReportStepKey, 'S2')
    assert.equal(context.simpleReportDraft.step_key, 'S2')
    assert.equal(context.simpleReportDraft.report_text, '刚刚提交的第一版')
    assert.equal(context.routeUpdates.length, 1)
  })
})

test('the final round demands an explicit confirmation before delivery', async () => {
  await withAdapter(async config => ({
    data: {},
    status: 200,
    statusText: 'OK',
    headers: {},
    config
  }), async () => {
    const context = simpleContext({
      selectedReportStepKey: 'S6',
      currentReportStep: simpleCase().workflow_instance.steps.at(-1),
      simpleReportDraft: {
        step_key: 'S6',
        report_text: '最终报告',
        review_note: '',
        final_gate_confirmed: false
      }
    })

    await context.completeSimpleReportStep()

    assert.equal(context.message, '请先确认已完成最终终审，再提交交付。')
    assert.equal(context.simpleReportSaving, false)
  })
})

test('an in-progress draft survives a same-node sync but a forced sync replaces it', () => {
  const context = simpleContext({
    selectedReportStepKey: 'S2',
    simpleReportVersions: [
      { id: 11, version_no: 1, version_label: 'v1.0', source_step_key: 'S1', report_text: '第一版完整报告' }
    ],
    simpleReportDraft: {
      step_key: 'S2',
      report_text: '咨询师输入到一半的修订',
      review_note: '正在补写',
      final_gate_confirmed: false
    }
  })

  context.syncSimpleReportDraft('S2')
  assert.equal(context.simpleReportDraft.report_text, '咨询师输入到一半的修订')

  context.syncSimpleReportDraft('S2', true)
  assert.equal(context.simpleReportDraft.report_text, '第一版完整报告')
  assert.equal(context.simpleReportDraft.review_note, '')
})

test('resetting the simple state clears versions and drafts', () => {
  const context = simpleContext({
    simpleReportVersions: [{ id: 11, version_no: 1 }],
    simpleReportDraft: { step_key: 'S1', report_text: '草稿' },
    simpleReportLoading: true,
    simpleReportSaving: true
  })

  context.resetSimpleReportState()

  assert.deepEqual(context.simpleReportVersions, [])
  assert.equal(context.simpleReportDraft, null)
  assert.equal(context.simpleReportLoading, false)
  assert.equal(context.simpleReportSaving, false)
})
