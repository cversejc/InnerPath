import apiClient from '../../utils/apiClient.js'

export async function getCurrentUserRequest() {
  const response = await apiClient.get('/users/me')
  return response.data
}

export async function updateUserProfileRequest(userData) {
  const response = await apiClient.put('/users/me', userData)
  return response.data
}

export async function changePassword(currentPassword, newPassword) {
  const response = await apiClient.post('/users/me/change-password', {
    current_password: currentPassword,
    new_password: newPassword
  })
  return response.data
}
