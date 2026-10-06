import apiClient from '../../utils/apiClient.js'

// Historical task status remains readable; new generation goes through service requests.
export async function getReportTask(taskId) {
  const response = await apiClient.get(`/reports/tasks/${taskId}`)
  return response.data
}

export async function getLatestReportTask() {
  const response = await apiClient.get('/reports/tasks/latest')
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

export async function downloadReportPdf(reportId) {
  return apiClient.get(`/reports/${reportId}/pdf`, { responseType: 'blob' })
}

export async function downloadReportPreviewPdf(report) {
  return apiClient.post('/reports/preview/pdf', { report }, { responseType: 'blob' })
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

export async function getAdminReportQualityIssues(params = {}) {
  const response = await apiClient.get('/admin/report-quality-issues', { params })
  return response.data
}

export async function getStaffUserReports(userId) {
  const response = await apiClient.get(`/staff/users/${userId}/reports`)
  return response.data
}
