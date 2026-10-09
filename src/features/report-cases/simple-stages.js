import { REPORT_WORKFLOW_STAGES } from './stages.js'

// The simplified workflow follows the same node catalog as the production
// workflow; only the per-node contract changes to user info + report text.
// This file owns the simplified presentation, not the production assets.
export const SIMPLE_REPORT_STEP_KEYS = REPORT_WORKFLOW_STAGES.map(stage => stage.stepKey)

export const SIMPLE_REPORT_STEPS = Object.fromEntries(
  REPORT_WORKFLOW_STAGES.map(stage => [
    stage.stepKey,
    {
      stepKey: stage.stepKey,
      shortName: stage.shortName,
      task: `以“${stage.name}”为重点，完成本节点的完整报告。`
    }
  ])
)

export function simpleReportStep(stepKey) {
  return SIMPLE_REPORT_STEPS[stepKey] || null
}

export function simpleReportStepLabel(stepKey, fallback = '处理步骤') {
  return simpleReportStep(stepKey)?.shortName || fallback
}

export function simpleReportVersionLabel(step) {
  const configured = Number(step?.config_snapshot?.output_version)
  const version = Number.isFinite(configured) && configured > 0 ? configured : Number(step?.sequence_no)
  return Number.isFinite(version) && version > 0 ? `v${version}.0` : '报告版本'
}
