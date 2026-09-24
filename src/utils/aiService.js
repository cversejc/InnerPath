import apiClient from './apiClient'

export function formatReportForFrontend(reportData) {
  const careerGuidance = reportData.career_guidance || reportData.careerGuidance || {}
  const suitablePaths = careerGuidance.suitable_paths || careerGuidance.suitablePaths || []
  return {
    id: reportData.id,
    basicInfo: reportData.basic_info || reportData.basicInfo || {},
    structuredSections: reportData.structured_sections || reportData.structuredSections || null,
    energyProfile: reportData.energy_profile || reportData.energyProfile || {},
    careerGuidance: {
      suitablePaths: Array.isArray(suitablePaths) ? suitablePaths : [],
      workStyle: careerGuidance.work_style || careerGuidance.workStyle || '',
      developmentSuggestions: careerGuidance.development_suggestions || careerGuidance.developmentSuggestions || []
    },
    relationshipPattern: reportData.relationship_pattern || reportData.relationshipPattern || {},
    personalGrowth: reportData.personal_growth || reportData.personalGrowth || {},
    summary: reportData.summary || '',
    aiGeneratedContent: reportData.ai_generated_content || reportData.aiGeneratedContent || null,
    createdAt: reportData.created_at || reportData.createdAt
  }
}

export async function getUserReports(page = 1, size = 10) {
  const response = await apiClient.get(`/reports?page=${page}&size=${size}`)
  return response.data
}

export async function getReportDetail(reportId) {
  const response = await apiClient.get(`/reports/${reportId}`)
  return response.data
}

export async function deleteReport(reportId) {
  const response = await apiClient.delete(`/reports/${reportId}`)
  return response.data
}

export default {
  getUserReports,
  getReportDetail,
  deleteReport
}
