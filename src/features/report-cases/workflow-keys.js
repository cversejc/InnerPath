export const DEFAULT_REPORT_WORKFLOW_KEY = 'report.production'
export const SIMPLE_REPORT_WORKFLOW_KEY = 'report.simple'

export const REPORT_WORKFLOW_OPTIONS = [
  {
    value: DEFAULT_REPORT_WORKFLOW_KEY,
    label: '标准流程',
    description: '多人分节点完成分析、写作与质量复核，适合需要完整拆解的申请。'
  },
  {
    value: SIMPLE_REPORT_WORKFLOW_KEY,
    label: '简化流程',
    description: '由同一位咨询师按标准流程的节点顺序连续完成，每个节点只交接用户信息与完整报告文本，适合希望更快拿到报告的申请。'
  }
]

export function reportWorkflowKey(reportCase) {
  const snapshot = reportCase?.application_snapshot
  const key = snapshot && typeof snapshot === 'object' ? snapshot.workflow_key : ''
  return String(key || '').trim() || DEFAULT_REPORT_WORKFLOW_KEY
}

export function isSimpleReportWorkflow(reportCase) {
  return reportWorkflowKey(reportCase) === SIMPLE_REPORT_WORKFLOW_KEY
}

// The workflow key lives in `report_case.application_snapshot`, but the staff
// console sometimes only has the service request at hand. Check every shape we
// may have before falling back to the production workflow.
export function reportWorkflowKeyFromSources(...sources) {
  for (const source of sources) {
    const key = typeof source === 'string'
      ? source
      : source?.application_snapshot?.workflow_key
        || source?.request_payload?.workflow_key
        || source?.workflow_key
    const normalized = String(key || '').trim()
    if (normalized) return normalized
  }
  return DEFAULT_REPORT_WORKFLOW_KEY
}

export function reportWorkflowOption(key) {
  const normalized = String(key || '').trim() || DEFAULT_REPORT_WORKFLOW_KEY
  return REPORT_WORKFLOW_OPTIONS.find(option => option.value === normalized) || REPORT_WORKFLOW_OPTIONS[0]
}

export function reportWorkflowLabel(key) {
  return reportWorkflowOption(key).label
}
