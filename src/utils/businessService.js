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

export async function getAdminUser(userId) {
  const response = await apiClient.get(`/admin/users/${userId}`)
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

export async function getAdminAuditLogs(params = {}) {
  const response = await apiClient.get('/admin/audit-logs', { params })
  return response.data
}

export async function updateAdminBooking(bookingId, data) {
  const response = await apiClient.patch(`/admin/bookings/${bookingId}`, data)
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
