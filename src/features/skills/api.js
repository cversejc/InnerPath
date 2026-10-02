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

export default {
  getSkillVersions,
  createSkillVersion,
  updateSkillVersion,
  publishSkillVersion,
  runSkill,
  getSkillRuns,
  getCaseSkillRuns
}
