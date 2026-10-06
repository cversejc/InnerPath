import apiClient from '../../utils/apiClient.js'

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

export async function getAdminUserTimeline(userId, limit = 30) {
  const response = await apiClient.get(`/admin/users/${userId}/timeline`, { params: { limit } })
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

export async function updateAdminUserRole(userId, role, consultantType) {
  const response = await apiClient.patch(`/admin/users/${userId}/role`, { role, ...(consultantType ? { consultant_type: consultantType } : {}) })
  return response.data
}

export async function updateAdminConsultantSpecialties(userId, specialties) {
  const response = await apiClient.patch(`/admin/users/${userId}/consultant-specialties`, { specialties })
  return response.data
}

export async function getAdminConsultantWorkload(periodDays = 30) {
  const response = await apiClient.get('/admin/consultants/workload', {
    params: { period_days: periodDays }
  })
  return response.data
}

export async function createStaffInvite(phone, role, consultantType) {
  const response = await apiClient.post('/admin/staff/invites', {
    phone,
    role,
    consultant_type: role === 'consultant' ? consultantType : null
  })
  return response.data
}

export async function getAdminAuditLogs(params = {}) {
  const response = await apiClient.get('/admin/audit-logs', { params })
  return response.data
}

export async function resetAdminUserPassword(userId, newPassword) {
  const response = await apiClient.post(`/admin/users/${userId}/password/reset`, {
    new_password: newPassword
  })
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
