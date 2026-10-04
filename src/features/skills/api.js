import apiClient from '../../utils/apiClient.js'

export async function getSkillVersions() {
  const response = await apiClient.get('/admin/skills')
  return response.data
}

export async function createSkillVersion(data) {
  const response = await apiClient.post('/admin/skills', data)
  return response.data
}

export async function updateSkillVersion(versionId, data) {
  const response = await apiClient.put(`/admin/skills/${versionId}`, data)
  return response.data
}

export async function publishSkillVersion(versionId) {
  const response = await apiClient.post(`/admin/skills/${versionId}/publish`)
  return response.data
}

export async function runSkill(versionId, data) {
  const response = await apiClient.post(`/admin/skills/${versionId}/runs`, data)
  return response.data
}

export async function getSkillRuns(versionId) {
  const response = await apiClient.get(`/admin/skills/${versionId}/runs`)
  return response.data
}

export async function getCaseSkillRuns(caseId) {
  const response = await apiClient.get(`/staff/report-cases/${caseId}/skill-runs`)
  return response.data
}

export async function recommendSkillExample(caseId, data) {
  const response = await apiClient.post(`/staff/report-cases/${caseId}/skill-examples`, data)
  return response.data
}

export async function recommendCalendarSkillExample(runId, data) {
  const response = await apiClient.post(`/admin/calendar-skill-runs/${runId}/examples`, data)
  return response.data
}

export async function getPublishedSkillExamples(params = {}) {
  const response = await apiClient.get('/staff/skill-examples', { params })
  return response.data
}

export async function getSkillExamples(params = {}) {
  const response = await apiClient.get('/admin/skill-examples', { params })
  return response.data
}

export async function updateSkillExample(exampleId, data) {
  const response = await apiClient.put(`/admin/skill-examples/${exampleId}/redaction`, data)
  return response.data
}

export async function publishSkillExample(exampleId) {
  const response = await apiClient.post(`/admin/skill-examples/${exampleId}/publish`)
  return response.data
}

export async function retireSkillExample(exampleId) {
  const response = await apiClient.post(`/admin/skill-examples/${exampleId}/retire`)
  return response.data
}

export async function createSkillExampleRevision(exampleId) {
  const response = await apiClient.post(`/admin/skill-examples/${exampleId}/revisions`)
  return response.data
}

export async function getSkillEvaluationCases(skillKey) {
  const response = await apiClient.get('/admin/skill-evaluation-cases', {
    params: skillKey ? { skill_key: skillKey } : {}
  })
  return response.data
}

export async function startSkillEvaluation(versionId, data) {
  const response = await apiClient.post(`/admin/skill-versions/${versionId}/evaluations`, data)
  return response.data
}

export async function getSkillEvaluation(batchId) {
  const response = await apiClient.get(`/admin/skill-evaluations/${batchId}`)
  return response.data
}

export async function getSkillEvaluationBatches(versionId) {
  const response = await apiClient.get(`/admin/skill-versions/${versionId}/evaluations`)
  return response.data
}

export default {
  getSkillVersions,
  createSkillVersion,
  updateSkillVersion,
  publishSkillVersion,
  runSkill,
  getSkillRuns,
  getCaseSkillRuns,
  recommendSkillExample,
  recommendCalendarSkillExample,
  getPublishedSkillExamples,
  getSkillExamples,
  updateSkillExample,
  publishSkillExample,
  retireSkillExample,
  createSkillExampleRevision,
  getSkillEvaluationCases,
  startSkillEvaluation,
  getSkillEvaluation,
  getSkillEvaluationBatches
}
