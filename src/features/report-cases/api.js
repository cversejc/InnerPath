import apiClient from '../../utils/apiClient.js'

export async function getReportCase(caseId) {
  const response = await apiClient.get(`/report-cases/${caseId}`)
  return response.data
}

export async function getReportCaseContent(caseId) {
  const response = await apiClient.get(`/report-cases/${caseId}/content`)
  return response.data
}

export async function startReportCaseStep(caseId, stepKey) {
  const response = await apiClient.post(`/report-cases/${caseId}/steps/${stepKey}/start`)
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
