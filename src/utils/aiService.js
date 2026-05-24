// AI 报告生成服务（调用后端API）
import axios from 'axios'
import apiConfig from './apiConfig'

// 创建axios实例
const apiClient = axios.create({
  baseURL: apiConfig.baseURL,
  timeout: apiConfig.timeout
})

// 请求拦截器 - 自动添加token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

/**
 * 调用后端API生成报告（异步）
 */
export async function generateReportWithAI(userData) {
  const { name, gender, birthYear, birthMonth, birthDay, birthHour, birthMinute, birthPlace, selectedTopics, additionalInfo } = userData

  try {
    // 构建请求数据
    const requestData = {
      name: name || '用户',
      gender: gender || 'male',
      birth_year: parseInt(birthYear),
      birth_month: parseInt(birthMonth),
      birth_day: parseInt(birthDay),
      birth_hour: birthHour ? parseInt(birthHour) : null,
      birth_minute: birthMinute ? parseInt(birthMinute) : null,
      birth_place: birthPlace || null,
      selected_topics: selectedTopics || [],
      additional_info: additionalInfo || null
    }

    console.log('发送报告生成请求:', requestData)

    // 1. 创建报告任务
    const createResponse = await apiClient.post('/reports', requestData)

    const { task_id } = createResponse.data
    console.log('任务创建成功，task_id:', task_id)

    // 2. 轮询任务状态
    const report = await pollTaskStatus(task_id)
    return report

  } catch (error) {
    console.error('报告生成失败:', error)
    console.error('错误详情:', error.response?.data)

    // 如果后端API调用失败，使用降级方案
    return generateBasicReport(userData)
  }
}

/**
 * 轮询任务状态
 */
async function pollTaskStatus(taskId, maxAttempts = 60) {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const response = await apiClient.get(`/reports/tasks/${taskId}`)
      const { status, report_id, report_data, error } = response.data

      if (status === 'completed') {
        // 如果有report_id（已登录用户），获取报告详情
        if (report_id) {
          const reportResponse = await apiClient.get(`/reports/${report_id}`)
          return formatReportForFrontend(reportResponse.data)
        }
        // 如果有report_data（游客用户），直接返回
        if (report_data) {
          return formatReportForFrontend(report_data)
        }
        throw new Error('报告数据缺失')
      } else if (status === 'failed') {
        throw new Error(error || '报告生成失败')
      }

      // 等待1秒后继续轮询
      await new Promise(resolve => setTimeout(resolve, 1000))
    } catch (error) {
      if (i === maxAttempts - 1) {
        throw error
      }
    }
  }

  throw new Error('报告生成超时')
}

/**
 * 格式化报告数据，确保前端可以正确显示
 */
function formatReportForFrontend(reportData) {
  console.log('格式化报告数据:', reportData)

  // 处理 career_guidance
  const careerGuidance = reportData.career_guidance || reportData.careerGuidance || {}
  const suitablePaths = careerGuidance.suitable_paths || careerGuidance.suitablePaths || []

  // 确保数据结构符合前端期望
  return {
    basicInfo: reportData.basic_info || reportData.basicInfo || {
      name: '用户',
      birthDate: reportData.birth_date || '',
      reportDate: reportData.report_date || new Date().toISOString().split('T')[0]
    },
    energyProfile: reportData.energy_profile || reportData.energyProfile || {
      type: '综合型',
      coreTraits: '独特的个人特质',
      description: '正在分析中...'
    },
    careerGuidance: {
      suitablePaths: Array.isArray(suitablePaths) ? suitablePaths : [],
      workStyle: careerGuidance.work_style || careerGuidance.workStyle || '',
      developmentSuggestions: careerGuidance.development_suggestions || careerGuidance.developmentSuggestions || []
    },
    relationshipPattern: reportData.relationship_pattern || reportData.relationshipPattern || {
      style: '',
      strengths: [],
      challenges: [],
      growthDirection: ''
    },
    personalGrowth: reportData.personal_growth || reportData.personalGrowth || {
      currentIssues: [],
      actionPlan: [],
      resources: []
    },
    summary: reportData.summary || '你是独特的个体，拥有无限的成长潜力。',
    aiGeneratedContent: reportData.ai_generated_content || reportData.ai_raw_content || reportData.aiGeneratedContent || null
  }
}

/**
 * 获取用户的报告列表
 */
export async function getUserReports(page = 1, size = 10) {
  const response = await apiClient.get(`/reports?page=${page}&size=${size}`)
  return response.data
}

/**
 * 获取报告详情
 */
export async function getReportDetail(reportId) {
  const response = await apiClient.get(`/reports/${reportId}`)
  return response.data
}

/**
 * 删除报告
 */
export async function deleteReport(reportId) {
  const response = await apiClient.delete(`/reports/${reportId}`)
  return response.data
}

/**
 * 生成基础版本的报告（当 AI 调用失败时使用）
 */
function generateBasicReport(userData) {
  const { birthYear, birthMonth, birthDay, selectedTopics } = userData

  // 简化的五行分析
  const sum = (parseInt(birthYear) + parseInt(birthMonth) + parseInt(birthDay)) % 5
  const elements = ['wood', 'fire', 'earth', 'metal', 'water']
  const dominantElement = elements[sum]

  const energyTypes = {
    wood: {
      name: '生长驱动型',
      traits: '创新求变、积极进取、富有创造力',
      description: '你的能量倾向于向外扩展和生长，喜欢探索新事物，具有强烈的成长动力。'
    },
    fire: {
      name: '表达驱动型',
      traits: '热情洋溢、善于表达、富有感染力',
      description: '你的能量倾向于向外散发和表达，喜欢与人互动，具有强烈的表现欲。'
    },
    earth: {
      name: '稳定承载型',
      traits: '踏实稳重、包容接纳、注重安全',
      description: '你的能量倾向于稳定和承载，喜欢建立秩序，具有强烈的责任感。'
    },
    metal: {
      name: '秩序驱动型',
      traits: '理性客观、追求完美、注重规则',
      description: '你的能量倾向于收敛和精炼，喜欢建立标准，具有强烈的原则性。'
    },
    water: {
      name: '智慧流动型',
      traits: '深思熟虑、善于观察、灵活变通',
      description: '你的能量倾向于向内流动和沉淀，喜欢深度思考，具有强烈的洞察力。'
    }
  }

  const energyType = energyTypes[dominantElement]

  return {
    basicInfo: {
      name: userData.name || '用户',
      birthDate: `${birthYear}-${birthMonth}-${birthDay}`,
      reportDate: new Date().toISOString().split('T')[0],
      generatedBy: 'Basic Algorithm'
    },
    energyProfile: {
      type: energyType.name,
      coreTraits: energyType.traits,
      description: energyType.description
    },
    careerGuidance: {
      suitablePaths: ['创意型工作', '分析型工作', '管理型工作'],
      workStyle: '根据个人特质发挥优势',
      developmentSuggestions: ['持续学习', '拓展人脉', '发挥优势']
    },
    relationshipPattern: {
      style: '独特的关系互动模式',
      strengths: ['真诚', '理解', '支持'],
      challenges: ['需要学习的方面'],
      growthDirection: '持续成长和改善'
    },
    personalGrowth: {
      currentIssues: selectedTopics.map(t => `关注${t}相关议题`),
      actionPlan: [
        {
          area: '能量管理',
          action: '每天预留30分钟独处时间，进行自我觉察',
          timeline: '立即开始'
        }
      ],
      resources: ['推荐书籍', '推荐课程', '推荐实践']
    },
    summary: `你是${energyType.name}，具有${energyType.traits}的特质。建议你从认识自己的能量模式开始，逐步建立适合自己的成长路径。`,
    aiGeneratedContent: null
  }
}

export default {
  generateReportWithAI,
  generateBasicReport
}
