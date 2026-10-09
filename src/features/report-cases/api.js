import apiClient from '../../utils/apiClient.js'

export async function getNodeReview(caseId, step) {
  return (await apiClient.get(`/report-cases/${caseId}/steps/${step}/review`)).data
}
export async function patchNodeReview(caseId, step, payload) {
  return (await apiClient.patch(`/report-cases/${caseId}/steps/${step}/review`, payload)).data
}
export async function nodeReviewCommand(caseId, step, command, payload) {
  return (await apiClient.post(`/report-cases/${caseId}/steps/${step}/review/${command}`, payload)).data
}
export async function approveNodeReviewCheckpoint(caseId, step, payload) {
  return (await apiClient.post(`/report-cases/${caseId}/steps/${step}/review/checkpoints`, payload)).data
}
export async function approveAndDeliver(caseId, payload) {
  return (await apiClient.post(`/report-cases/${caseId}/approve-and-deliver`, payload)).data
}

export async function getReportCase(caseId) {
  const response = await apiClient.get(`/report-cases/${caseId}`)
  return response.data
}

export async function importReportCaseContent(caseId, payload) {
  const response = await apiClient.post(`/report-cases/${caseId}/import-report`, payload)
  return response.data
}

export async function requestReportCaseInfo(caseId, stepKey, reason) {
  const response = await apiClient.post(
    `/report-cases/${caseId}/steps/${stepKey}/request-info`,
    { reason }
  )
  return response.data
}

export async function submitReportCaseSupplement(caseId, payload) {
  const response = await apiClient.post(`/report-cases/${caseId}/supplements`, payload)
  return response.data
}

export async function getReportCaseContent(caseId) {
  const response = await apiClient.get(`/report-cases/${caseId}/content`)
  return response.data
}

export async function getReportCaseQuality(caseId) {
  const response = await apiClient.get(`/report-cases/${caseId}/quality`)
  return response.data
}

export async function runReportCaseQuality(caseId, payload) {
  const response = await apiClient.post(`/report-cases/${caseId}/quality/run`, payload)
  return response.data
}

export async function resolveReportCaseQualityIssue(caseId, issueId, payload) {
  const response = await apiClient.post(
    `/report-cases/${caseId}/quality/issues/${issueId}/resolve`,
    payload
  )
  return response.data
}

export async function resolveReportCaseQualityIssueGroup(caseId, payload) {
  const response = await apiClient.post(
    `/report-cases/${caseId}/quality/issues/resolve-group`,
    payload
  )
  return response.data
}

export async function approveReportCaseFinalGate(caseId, payload) {
  const response = await apiClient.post(`/report-cases/${caseId}/final-gate/approve`, payload)
  return response.data
}

export async function deliverReportCase(caseId) {
  const response = await apiClient.post(`/report-cases/${caseId}/deliver`)
  return response.data
}

export async function getReportCaseVersions(caseId) {
  const response = await apiClient.get(`/report-cases/${caseId}/versions`)
  return response.data
}

export async function getSimpleReportCaseVersions(caseId) {
  const response = await apiClient.get(`/report-cases/${caseId}/simple/versions`)
  return response.data
}

export async function completeSimpleReportCaseStep(caseId, stepKey, payload) {
  const response = await apiClient.post(
    `/report-cases/${caseId}/simple/steps/${stepKey}/complete`,
    payload
  )
  return response.data
}

export async function getReportCaseNarrative(caseId) {
  const response = await apiClient.get(`/report-cases/${caseId}/narrative`)
  return response.data
}

export async function startReportCaseStep(caseId, stepKey) {
  const response = await apiClient.post(`/report-cases/${caseId}/steps/${stepKey}/start`)
  return response.data
}

export async function getReportCaseStepCompletionGate(caseId, stepKey) {
  const response = await apiClient.get(`/report-cases/${caseId}/steps/${stepKey}/completion-gate`)
  return response.data
}

export async function startReportCaseAnalysisDraft(caseId, stepKey, payload) {
  const response = await apiClient.post(
    `/report-cases/${caseId}/steps/${stepKey}/analysis-drafts`,
    payload
  )
  return response.data
}

export async function applyReportCaseAnalysisCandidates(caseId, stepKey, runId) {
  const response = await apiClient.post(
    `/report-cases/${caseId}/steps/${stepKey}/analysis-drafts/${runId}/apply`
  )
  return response.data
}

export async function calculateReportCaseFoundation(caseId, stepKey = 'S1') {
  const response = await apiClient.post(
    `/report-cases/${caseId}/steps/${stepKey}/foundation/calculate`
  )
  return response.data
}

export async function correctReportCaseFoundation(caseId, stepKey, payload) {
  const response = await apiClient.put(
    `/report-cases/${caseId}/steps/${stepKey}/foundation`,
    payload
  )
  return response.data
}

export async function applyReportCaseAnalysisFinding(caseId, stepKey, runId, findingKey, payload) {
  const response = await apiClient.post(
    `/report-cases/${caseId}/steps/${stepKey}/analysis-drafts/${runId}/findings/${encodeURIComponent(findingKey)}/apply`,
    payload
  )
  return response.data
}

export async function applyReportCaseAnalysisFragment(caseId, stepKey, runId, fragmentKey, payload) {
  const response = await apiClient.post(
    `/report-cases/${caseId}/steps/${stepKey}/analysis-drafts/${runId}/fragments/${encodeURIComponent(fragmentKey)}/apply`,
    payload
  )
  return response.data
}

export async function completeReportCaseStep(caseId, stepKey, result = {}) {
  const response = await apiClient.post(`/report-cases/${caseId}/steps/${stepKey}/complete`, {
    result_json: result
  })
  return response.data
}

export async function returnReportCaseStep(caseId, stepKey, targetStepKey, reason) {
  const response = await apiClient.post(`/report-cases/${caseId}/steps/${stepKey}/return`, {
    target_step_key: targetStepKey,
    reason
  })
  return response.data
}

export async function reopenReportCaseStep(caseId, stepKey) {
  const response = await apiClient.post(`/report-cases/${caseId}/steps/${stepKey}/reopen`)
  return response.data
}

export async function saveReportCaseFinding(caseId, stepKey, findingKey, payload) {
  const response = await apiClient.put(
    `/report-cases/${caseId}/steps/${stepKey}/findings/${encodeURIComponent(findingKey)}`,
    payload
  )
  return response.data
}

export async function saveReportCaseFragment(caseId, stepKey, fragmentKey, payload) {
  const response = await apiClient.put(
    `/report-cases/${caseId}/steps/${stepKey}/fragments/${encodeURIComponent(fragmentKey)}`,
    payload
  )
  return response.data
}

export async function generateReportNarrativeCandidates(caseId, stepKey, payload) {
  const response = await apiClient.post(
    `/report-cases/${caseId}/steps/${stepKey}/narrative-candidates`,
    payload
  )
  return response.data
}

export async function confirmReportCaseNarrativePlan(caseId, payload) {
  const response = await apiClient.post(`/report-cases/${caseId}/narrative-plans/confirm`, payload)
  return response.data
}

export async function startReportCaseGeneration(caseId, payload) {
  const response = await apiClient.post(`/report-cases/${caseId}/narrative/generation`, payload)
  return response.data
}

export async function runReportCaseCoherenceCheck(caseId, payload) {
  const response = await apiClient.post(
    `/report-cases/${caseId}/narrative/coherence-check`,
    payload
  )
  return response.data
}

export async function generateReportCaseFragment(caseId, stepKey, payload) {
  const response = await apiClient.post(
    `/report-cases/${caseId}/steps/${stepKey}/fragments/generate`,
    payload
  )
  return response.data
}
