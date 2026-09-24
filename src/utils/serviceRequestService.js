import apiClient from './apiClient'

// 用户端申请
export async function createServiceRequest(data) {
  const response = await apiClient.post('/service-requests', data)
  return response.data
}

export async function getMyServiceRequests(params = {}) {
  const response = await apiClient.get('/service-requests', { params })
  return response.data
}

export async function getMyServiceRequest(requestId) {
  const response = await apiClient.get(`/service-requests/${requestId}`)
  return response.data
}

export async function updateServiceRequest(requestId, data) {
  const response = await apiClient.patch(`/service-requests/${requestId}`, data)
  return response.data
}

export async function resubmitServiceRequest(requestId) {
  const response = await apiClient.post(`/service-requests/${requestId}/resubmit`)
  return response.data
}

export async function withdrawServiceRequest(requestId) {
  const response = await apiClient.post(`/service-requests/${requestId}/withdraw`)
  return response.data
}

// 咨询师工作台
export async function getStaffServiceRequests(params = {}) {
  const response = await apiClient.get('/staff/service-requests', { params })
  return response.data
}

export async function acceptStaffServiceRequest(requestId) {
  const response = await apiClient.post(`/staff/service-requests/${requestId}/accept`)
  return response.data
}

export async function getStaffServiceRequestWorkspace(requestId) {
  const response = await apiClient.get(`/staff/service-requests/${requestId}`)
  return response.data
}

export async function startStaffAIDraft(requestId) {
  const response = await apiClient.post(`/staff/service-requests/${requestId}/ai-draft`)
  return response.data
}

export async function getStaffServiceRequestTask(taskId) {
  const response = await apiClient.get(`/staff/service-request-tasks/${taskId}`)
  return response.data
}

export async function saveStaffDraft(requestId, payload, expectedVersion = null) {
  const response = await apiClient.put(`/staff/service-requests/${requestId}/draft`, {
    payload,
    expected_version: expectedVersion
  })
  return response.data
}

export async function requestStaffInfo(requestId, reason) {
  const response = await apiClient.post(`/staff/service-requests/${requestId}/request-info`, { reason })
  return response.data
}

export async function retryStaffAIDraft(requestId, confirmOverwrite = false) {
  const response = await apiClient.post(`/staff/service-requests/${requestId}/retry-ai`, {
    confirm_overwrite: confirmOverwrite
  })
  return response.data
}

export async function deliverStaffServiceRequest(requestId) {
  const response = await apiClient.post(`/staff/service-requests/${requestId}/deliver`)
  return response.data
}

// 管理员介入
export async function getAdminServiceRequests(params = {}) {
  const response = await apiClient.get('/admin/service-requests', { params })
  return response.data
}

export async function updateAdminServiceRequestAssignment(requestId, consultantId) {
  const response = await apiClient.patch(`/admin/service-requests/${requestId}/assignment`, {
    consultant_id: consultantId
  })
  return response.data
}

export async function rejectAdminServiceRequest(requestId, reason) {
  const response = await apiClient.post(`/admin/service-requests/${requestId}/reject`, { reason })
  return response.data
}

export default {
  createServiceRequest,
  getMyServiceRequests,
  getMyServiceRequest,
  updateServiceRequest,
  resubmitServiceRequest,
  withdrawServiceRequest,
  getStaffServiceRequests,
  acceptStaffServiceRequest,
  getStaffServiceRequestWorkspace,
  startStaffAIDraft,
  getStaffServiceRequestTask,
  saveStaffDraft,
  requestStaffInfo,
  retryStaffAIDraft,
  deliverStaffServiceRequest,
  getAdminServiceRequests,
  updateAdminServiceRequestAssignment,
  rejectAdminServiceRequest
}
