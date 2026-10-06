import apiClient from '../../utils/apiClient.js'

export async function submitServiceFeedback(data) {
  const response = await apiClient.post('/service-feedback', data)
  return response.data
}

export async function getMyServiceFeedback() {
  const response = await apiClient.get('/service-feedback/mine')
  return response.data
}

export async function getAdminServiceFeedback(params = {}) {
  const response = await apiClient.get('/admin/service-feedback', { params })
  return response.data
}

export async function getAdminServiceQualitySummary(periodDays = 30) {
  const response = await apiClient.get('/admin/service-feedback/summary', {
    params: { period_days: periodDays }
  })
  return response.data
}

export async function updateAdminServiceFeedback(feedbackId, data) {
  const response = await apiClient.patch(`/admin/service-feedback/${feedbackId}`, data)
  return response.data
}
