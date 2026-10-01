import apiClient from '../../utils/apiClient'

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

export async function getAdminBookings(params = {}) {
  const response = await apiClient.get('/admin/bookings', { params })
  return response.data
}

export async function getAdminUserBookings(userId, params = {}) {
  const response = await apiClient.get(`/admin/users/${userId}/bookings`, { params })
  return response.data
}

export async function updateAdminBooking(bookingId, data) {
  const response = await apiClient.patch(`/admin/bookings/${bookingId}`, data)
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
