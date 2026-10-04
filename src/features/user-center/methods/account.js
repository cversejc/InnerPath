import { changePassword, updateUserProfile } from '../../users/service.js'
import { changePhone, deactivateAccount as deactivateUserAccount, requestPhoneChangeCode } from '../../auth/session.js'
import { clearAuthState, logout as logoutUser, setAuthenticatedUser } from '../../../stores/auth.js'
import { buildProfilePayload, validateProfile } from '../../users/profile.js'

export default {
  async saveSettings() {
    this.settingsError = ''
    this.settingsErrors = validateProfile(this.settings)
    if (Object.keys(this.settingsErrors).length) {
      this.settingsError = '请先检查本人画像中的必填项。'
      return
    }
    this.savingSettings = true
    try {
      const user = await updateUserProfile(buildProfilePayload(this.settings))
      setAuthenticatedUser(user)
      this.userName = user.name
      this.settingsError = ''
      this.message = '本人画像已保存（版本 v' + (user.profile_version || 1) + '）'
    } catch (error) {
      this.settingsError = error.response?.data?.detail || '画像保存失败'
    } finally {
      this.savingSettings = false
    }
  },
  async savePassword() {
    this.savingPassword = true
    try {
      await changePassword(this.passwordForm.current, this.passwordForm.next)
      this.passwordForm = { current: '', next: '' }
      this.message = '密码已更新。'
    } catch (error) {
      this.message = error.response?.data?.detail || '密码更新失败'
    } finally {
      this.savingPassword = false
    }
  },
  async requestPhoneChangeCode() {
    this.phoneChangeError = ''
    this.phoneChangeMessage = ''
    if (!/^\d{11}$/.test(this.phoneChangeForm.newPhone || '')) {
      this.phoneChangeError = '请输入有效的 11 位新手机号。'
      return
    }
    this.requestingPhoneCode = true
    try {
      await requestPhoneChangeCode(this.phoneChangeForm.newPhone)
      this.phoneChangeMessage = '验证码已发送，请查收新手机号短信。'
    } catch (error) {
      this.phoneChangeError = error.response?.data?.detail || '验证码发送失败，请稍后重试。'
    } finally {
      this.requestingPhoneCode = false
    }
  },
  async savePhoneChange() {
    this.phoneChangeError = ''
    this.phoneChangeMessage = ''
    if (!/^\d{11}$/.test(this.phoneChangeForm.newPhone || '')) {
      this.phoneChangeError = '请输入有效的 11 位新手机号。'
      return
    }
    if (!/^\d{6}$/.test(this.phoneChangeForm.code || '')) {
      this.phoneChangeError = '请输入 6 位短信验证码。'
      return
    }
    if (!this.phoneChangeForm.currentPassword) {
      this.phoneChangeError = '请输入当前密码。'
      return
    }
    this.savingPhoneChange = true
    try {
      const user = await changePhone(
        this.phoneChangeForm.newPhone,
        this.phoneChangeForm.code,
        this.phoneChangeForm.currentPassword
      )
      this.accountPhone = user.phone
      setAuthenticatedUser(user)
      this.phoneChangeForm = { newPhone: '', code: '', currentPassword: '' }
      this.phoneChangeMessage = '登录手机号已更新。'
    } catch (error) {
      this.phoneChangeError = error.response?.data?.detail || '手机号更新失败，请检查信息后重试。'
    } finally {
      this.savingPhoneChange = false
    }
  },
  async deactivateAccount(currentPassword) {
    this.deactivationError = ''
    this.deactivating = true
    try {
      await deactivateUserAccount(currentPassword)
      clearAuthState()
      await this.$router.replace({ path: '/auth/login', query: { notice: 'account-deactivated' } })
    } catch (error) {
      this.deactivationError = error.response?.data?.detail || '账号停用失败，请稍后重试。'
    } finally {
      this.deactivating = false
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
