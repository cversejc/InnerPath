import { acceptStaffInvite, login, register } from '../session.js'
import { setAuthenticatedUser } from '../../../stores/auth.js'

export default {
  async submit() {
    this.errorMessage = ''
    this.successMessage = ''
    this.submitting = true
    try {
      let response
      if (this.mode === 'login') {
        response = await login(this.form.phone, this.form.password)
      } else if (this.mode === 'register') {
        response = await register(this.form.phone, this.form.password, this.form.name)
      } else if (this.mode === 'invite') {
        response = await acceptStaffInvite(this.form.token, this.form.phone, this.form.password, this.form.name)
      } else {
        return
      }
      setAuthenticatedUser(response.user)
      const redirect = this.$route.query.redirect
      const fallback = response.user.role === 'admin'
        ? '/admin'
        : response.user.role === 'consultant'
          ? '/staff'
          : '/pages/home/home'
      await this.$router.replace(redirect || fallback)
    } catch (error) {
      const detail = error.response?.data?.detail
      this.errorMessage = detail === 'Password setup required'
        ? '该账号尚未设置密码，请联系管理员完成首次密码设置'
        : detail || '操作失败，请检查信息后重试'
    } finally {
      this.submitting = false
    }
  }
}
