import apiClient from '../../utils/apiClient.js'

export async function getMyCalendars() {
  const response = await apiClient.get('/calendar/me')
  return response.data
}

export async function getCalendarRequests() {
  const response = await apiClient.get('/calendar/requests')
  return response.data
}

export async function createCalendarRequest(requestData) {
  const response = await apiClient.post('/calendar/requests', requestData, { timeout: 150000 })
  return response.data
}

export async function retryCalendarRequest(requestId) {
  const response = await apiClient.post(`/calendar/requests/${requestId}/retry`)
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

export async function getAdminDecisionLogs(params = {}) {
  const response = await apiClient.get('/admin/decision-logs', { params })
  return response.data
}

export async function getAdminUserDecisionLogs(userId, params = {}) {
  const response = await apiClient.get(`/admin/users/${userId}/decision-logs`, { params })
  return response.data
}

export async function getAdminCalendars(userId) {
  const response = await apiClient.get(`/admin/users/${userId}/calendars`)
  return response.data
}

export async function getAdminCalendarRequests(params = {}) {
  const response = await apiClient.get('/admin/calendar-requests', { params })
  return response.data
}

export async function retryAdminCalendarRequest(requestId) {
  const response = await apiClient.post(`/admin/calendar-requests/${requestId}/retry`)
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
