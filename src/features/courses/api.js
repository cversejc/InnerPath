import apiClient from '../../utils/apiClient'

export async function getMyCourses() {
  const response = await apiClient.get('/courses/my-courses')
  return response.data
}

export async function getCourses() {
  const response = await apiClient.get('/courses')
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
