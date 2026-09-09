import apiClient from './apiClient'

export async function getBookings(status) {
  const query = status ? `?status=${encodeURIComponent(status)}` : ''
  const response = await apiClient.get(`/bookings${query}`)
  return response.data
}

export async function createBooking(bookingData) {
  const response = await apiClient.post('/bookings', bookingData)
  return response.data
}

export async function cancelBooking(bookingId, reason = null) {
  const response = await apiClient.post(`/bookings/${bookingId}/cancel`, { reason })
  return response.data
}

export async function getMyCourses() {
  const response = await apiClient.get('/courses/my-courses')
  return response.data
}

export async function getCourses() {
  const response = await apiClient.get('/courses')
  return response.data
}

export async function getMyCalendars() {
  const response = await apiClient.get('/calendar/me')
  return response.data
}

export async function getMyDecisionLogs(params = {}) {
  const response = await apiClient.get('/calendar/decision-logs', { params })
  return response.data
}

export async function createDecisionLog(logData) {
  const response = await apiClient.post('/calendar/decision-logs', logData)
  return response.data
}

export async function deleteDecisionLog(logId) {
  const response = await apiClient.delete(`/calendar/decision-logs/${logId}`)
  return response.data
}

export async function getAdminUsers(params = {}) {
  const response = await apiClient.get('/admin/users', { params })
  return response.data
}

export async function getAllAdminUsers(params = {}) {
  const size = Math.min(Number(params.size) || 100, 100)
  const first = await getAdminUsers({ ...params, page: 1, size })
  const pageCount = Math.ceil((first.total || 0) / size)
  if (pageCount <= 1) return first
  const remaining = await Promise.all(
    Array.from({ length: pageCount - 1 }, (_, index) => getAdminUsers({ ...params, page: index + 2, size }))
  )
  return { ...first, items: [first.items || [], ...remaining.map(page => page.items || [])].flat() }
}

export async function getAdminDashboard(range = '30d') {
  const response = await apiClient.get('/admin/dashboard/overview', { params: { range } })
  return response.data
}

export async function getAdminUser(userId) {
  const response = await apiClient.get(`/admin/users/${userId}`)
  return response.data
}

export async function getAdminUserSummary(userId) {
  const response = await apiClient.get(`/admin/users/${userId}/summary`)
  return response.data
}

export async function updateAdminUserProfile(userId, data) {
  const response = await apiClient.patch(`/admin/users/${userId}`, data)
  return response.data
}

export async function updateAdminUserStatus(userId, isActive) {
  const response = await apiClient.patch(`/admin/users/${userId}/status`, { is_active: isActive })
  return response.data
}

export async function updateAdminUserRole(userId, role) {
  const response = await apiClient.patch(`/admin/users/${userId}/role`, { role })
  return response.data
}

export async function createStaffInvite(phone, role) {
  const response = await apiClient.post('/admin/staff/invites', { phone, role })
  return response.data
}

export async function getAdminBookings(params = {}) {
  const response = await apiClient.get('/admin/bookings', { params })
  return response.data
}

export async function getAdminUserBookings(userId, params = {}) {
  const response = await apiClient.get(`/admin/users/${userId}/bookings`, { params })
  return response.data
}

export async function getAdminUserCourses(userId) {
  const response = await apiClient.get(`/admin/courses/users/${userId}`)
  return response.data
}

export async function updateAdminUserCourseProgress(userId, courseId, data) {
  const response = await apiClient.patch(`/admin/courses/users/${userId}/${courseId}/progress`, data)
  return response.data
}

export async function getAdminDecisionLogs(params = {}) {
  const response = await apiClient.get('/admin/decision-logs', { params })
  return response.data
}

export async function getAdminUserDecisionLogs(userId, params = {}) {
  const response = await apiClient.get(`/admin/users/${userId}/decision-logs`, { params })
  return response.data
}

export async function getAdminAuditLogs(params = {}) {
  const response = await apiClient.get('/admin/audit-logs', { params })
  return response.data
}

export async function updateAdminBooking(bookingId, data) {
  const response = await apiClient.patch(`/admin/bookings/${bookingId}`, data)
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

export async function resetAdminUserPassword(userId, newPassword) {
  const response = await apiClient.post(`/admin/users/${userId}/password/reset`, {
    new_password: newPassword
  })
  return response.data
}

export async function getStaffBookings(params = {}) {
  const response = await apiClient.get('/staff/bookings', { params })
  return response.data
}

export async function updateStaffBooking(bookingId, data) {
  const response = await apiClient.patch(`/staff/bookings/${bookingId}`, data)
  return response.data
}

export async function getAdminCalendars(userId) {
  const response = await apiClient.get(`/admin/users/${userId}/calendars`)
  return response.data
}

export async function createAdminCalendar(userId, data) {
  const response = await apiClient.post(`/admin/users/${userId}/calendars`, data)
  return response.data
}

export async function createAdminCalendarDraft(calendarId) {
  const response = await apiClient.post(`/admin/calendars/${calendarId}/draft`)
  return response.data
}

export async function importAdminCalendar(data) {
  const response = await apiClient.post('/admin/calendars/import', data)
  return response.data
}

export async function updateAdminCalendar(calendarId, data) {
  const response = await apiClient.put(`/admin/calendars/${calendarId}`, data)
  return response.data
}

export async function publishAdminCalendar(calendarId) {
  const response = await apiClient.post(`/admin/calendars/${calendarId}/publish`)
  return response.data
}

export async function archiveAdminCalendar(calendarId) {
  const response = await apiClient.post(`/admin/calendars/${calendarId}/archive`)
  return response.data
}

export async function getStaffUserCalendars(userId) {
  const response = await apiClient.get(`/staff/users/${userId}/calendar`)
  return response.data
}

export async function getStaffUserReports(userId) {
  const response = await apiClient.get(`/staff/users/${userId}/reports`)
  return response.data
}

export async function downloadAdminExport(resource, params = {}) {
  const response = await apiClient.get(`/admin/exports/${resource}.csv`, {
    params,
    responseType: 'blob'
  })
  const disposition = response.headers['content-disposition'] || ''
  const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] || `${resource}.csv`
  const url = window.URL.createObjectURL(response.data)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.URL.revokeObjectURL(url)
  return true
}
