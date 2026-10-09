import assert from 'node:assert/strict'
import test from 'node:test'
import {
  DEFAULT_REPORT_WORKFLOW_KEY,
  SIMPLE_REPORT_WORKFLOW_KEY,
  isSimpleReportWorkflow,
  reportWorkflowKey,
  reportWorkflowKeyFromSources,
  reportWorkflowLabel,
  reportWorkflowOption
} from './workflow-keys.js'

test('legacy and unknown cases fall back to the production workflow', () => {
  assert.equal(reportWorkflowKey(null), DEFAULT_REPORT_WORKFLOW_KEY)
  assert.equal(reportWorkflowKey({ application_snapshot: {} }), DEFAULT_REPORT_WORKFLOW_KEY)
  assert.equal(
    reportWorkflowKey({ application_snapshot: { workflow_key: '  ' } }),
    DEFAULT_REPORT_WORKFLOW_KEY
  )
  assert.equal(
    reportWorkflowKeyFromSources({ workflow_key: '' }, null),
    DEFAULT_REPORT_WORKFLOW_KEY
  )
})

test('a case is simplified only when the frozen snapshot says so', () => {
  const simpleCase = { application_snapshot: { workflow_key: SIMPLE_REPORT_WORKFLOW_KEY } }
  assert.equal(reportWorkflowKey(simpleCase), SIMPLE_REPORT_WORKFLOW_KEY)
  assert.equal(isSimpleReportWorkflow(simpleCase), true)
  assert.equal(isSimpleReportWorkflow({ application_snapshot: {} }), false)
})

test('workflow key lookup reads request, payload and case shapes in order', () => {
  assert.equal(
    reportWorkflowKeyFromSources({ workflow_key: SIMPLE_REPORT_WORKFLOW_KEY }),
    SIMPLE_REPORT_WORKFLOW_KEY
  )
  assert.equal(
    reportWorkflowKeyFromSources(null, { request_payload: { workflow_key: SIMPLE_REPORT_WORKFLOW_KEY } }),
    SIMPLE_REPORT_WORKFLOW_KEY
  )
  assert.equal(
    reportWorkflowKeyFromSources({ application_snapshot: { workflow_key: SIMPLE_REPORT_WORKFLOW_KEY } }, { workflow_key: DEFAULT_REPORT_WORKFLOW_KEY }),
    SIMPLE_REPORT_WORKFLOW_KEY
  )
  assert.equal(reportWorkflowKeyFromSources(SIMPLE_REPORT_WORKFLOW_KEY), SIMPLE_REPORT_WORKFLOW_KEY)
})

test('workflow options expose a human label and default safely', () => {
  assert.equal(reportWorkflowLabel(SIMPLE_REPORT_WORKFLOW_KEY), '简化流程')
  assert.equal(reportWorkflowLabel('report.experimental'), '标准流程')
  assert.equal(reportWorkflowOption(null).value, DEFAULT_REPORT_WORKFLOW_KEY)
})
