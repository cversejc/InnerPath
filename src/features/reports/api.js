import apiClient from '../../utils/apiClient'

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
