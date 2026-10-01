import {
  getCurrentUserRequest,
  updateUserProfileRequest
} from './api.js'

function cacheUser(user) {
  sessionStorage.setItem('user', JSON.stringify(user))
  return user
}

export async function getCurrentUser() {
  return cacheUser(await getCurrentUserRequest())
}

export async function updateUserProfile(userData) {
  return cacheUser(await updateUserProfileRequest(userData))
}

export { changePassword } from './api.js'
