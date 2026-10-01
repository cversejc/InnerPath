import {
  createReportTask,
  getReportDetail,
  getReportTask
} from './api.js'

export function buildReportRequest(userData) {
  if (userData.context || userData.profile_version) {
    return {
      profile_version: userData.profile_version ? Number(userData.profile_version) : null,
      context: {
        focus_topics: userData.context?.focus_topics || [],
        current_challenge: userData.context?.current_challenge?.trim() || null,
        expected_outcomes: userData.context?.expected_outcomes || [],
        issue_duration: userData.context?.issue_duration || null,
        impact_level: userData.context?.impact_level || null,
        decision_status: userData.context?.decision_status || null,
        decision_description: userData.context?.decision_description?.trim() || null,
        decision_style: userData.context?.decision_style || [],
        additional_info: userData.context?.additional_info?.trim() || null
      }
    }
  }

  return {
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
}

export async function generateReportWithAI(userData) {
  const task = await createReportTask(buildReportRequest(userData))
  return pollTaskStatus(task.task_id)
}

async function pollTaskStatus(taskId, maxAttempts = 120) {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const task = await getReportTask(taskId)
    if (task.status === 'completed' && task.report_id) {
      return formatReportForFrontend(await getReportDetail(task.report_id))
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
