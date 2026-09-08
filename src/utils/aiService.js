import apiClient from './apiClient'

export async function generateReportWithAI(userData) {
  const requestData = {
    name: userData.name || null,
    gender: userData.gender,
    birth_year: Number(userData.birthYear),
    birth_month: Number(userData.birthMonth),
    birth_day: Number(userData.birthDay),
    birth_hour: userData.birthHour === '' ? null : Number(userData.birthHour),
    birth_minute: userData.birthMinute === '' ? null : Number(userData.birthMinute),
    birth_place: userData.birthPlace || null,
    calendar_type: userData.calendarType || 'solar',
    selected_topics: userData.selectedTopics || [],
    additional_info: userData.additionalInfo || null
  }

  const createResponse = await apiClient.post('/reports', requestData)
  return pollTaskStatus(createResponse.data.task_id)
}

async function pollTaskStatus(taskId, maxAttempts = 120) {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const response = await apiClient.get(`/reports/tasks/${taskId}`)
    const task = response.data
    if (task.status === 'completed' && task.report_id) {
      const reportResponse = await apiClient.get(`/reports/${task.report_id}`)
      return formatReportForFrontend(reportResponse.data)
    }
    if (task.status === 'failed') {
      throw new Error(task.error || '报告生成失败')
    }
    await new Promise(resolve => setTimeout(resolve, 1000))
  }
  throw new Error('报告生成超时')
}

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
  generateReportWithAI,
  getUserReports,
  getReportDetail,
  deleteReport
}
