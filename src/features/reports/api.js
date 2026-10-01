import apiClient from '../../utils/apiClient.js'

export async function createReportTask(requestData) {
  const response = await apiClient.post('/reports', requestData)
  return response.data
}

export async function getReportTask(taskId) {
  const response = await apiClient.get(`/reports/tasks/${taskId}`)
  return response.data
}

export async function getUserReports(page = 1, size = 10) {
  const response = await apiClient.get('/reports', { params: { page, size } })
  return response.data
}

export async function getReportDetail(reportId) {
  const response = await apiClient.get(`/reports/${reportId}`)
  return response.data
}

export async function getLatestReportContext() {
  const response = await apiClient.get('/reports/latest/context')
  return response.data
}

export async function deleteReport(reportId) {
  const response = await apiClient.delete(`/reports/${reportId}`)
  return response.data
}

export async function getAdminReports(params = {}) {
  const response = await apiClient.get('/admin/reports', { params })
  return response.data
}

export async function getAdminReport(reportId) {
  const response = await apiClient.get(`/admin/reports/${reportId}`)
  return response.data
}

export async function getAdminReportTasks(params = {}) {
  const response = await apiClient.get('/admin/report-tasks', { params })
  return response.data
}

export async function retryAdminReportTask(taskId) {
  const response = await apiClient.post(`/admin/report-tasks/${taskId}/retry`)
  return response.data
}

export async function getStaffUserReports(userId) {
  const response = await apiClient.get(`/staff/users/${userId}/reports`)
  return response.data
}
