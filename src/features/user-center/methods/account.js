import { changePassword, updateUserProfile } from '../../users/service.js'
import { logout as logoutUser, setAuthenticatedUser } from '../../../stores/auth.js'
import { buildProfilePayload, validateProfile } from '../../users/profile.js'

export default {
  async saveSettings() {
    this.settingsError = ''
    this.settingsErrors = validateProfile(this.settings)
    if (Object.keys(this.settingsErrors).length) {
      this.settingsError = '请先检查档案中的必填项。'
      return
    }
    this.savingSettings = true
    try {
      const user = await updateUserProfile(buildProfilePayload(this.settings))
      setAuthenticatedUser(user)
      this.userName = user.name
      this.profileCompletion = Number(user.profile_completion || 0)
      this.profileLastConfirmedAt = user.profile_last_confirmed_at || null
      this.settingsError = ''
      this.message = '个人档案已保存（版本 v' + (user.profile_version || 1) + '）'
    } catch (error) {
      this.settingsError = error.response?.data?.detail || '设置保存失败'
    } finally {
      this.savingSettings = false
    }
  },
  async savePassword() {
    this.savingPassword = true
    try {
      await changePassword(this.passwordForm.current, this.passwordForm.next)
      this.passwordForm = { current: '', next: '' }
      this.message = '密码已更新，请重新登录其他设备'
    } catch (error) {
      this.message = error.response?.data?.detail || '密码更新失败'
    } finally {
      this.savingPassword = false
    }
  },
  async handleLogout() {
    this.loggingOut = true
    try {
      await logoutUser()
    } catch {
      // 本地会话由 logoutUser 在 finally 中清理，即使服务端请求失败也能退出当前设备。
    } finally {
      await this.$router.replace('/auth/login')
    }
  }
}
