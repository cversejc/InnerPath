import { acceptStaffInvite, login, register, resetPassword } from '../session.js'
import { setAuthenticatedUser } from '../../../stores/auth.js'

export default {
  async submit() {
    this.errorMessage = ''
    this.successMessage = ''
    if (this.mode === 'reset' && this.form.password !== this.form.passwordConfirmation) {
      this.errorMessage = '两次输入的新密码不一致'
      return
    }

    this.submitting = true
    try {
      let response
      if (this.mode === 'login') {
        response = await login(this.form.phone, this.form.password)
      } else if (this.mode === 'register') {
        response = await register(this.form.phone, this.form.password, this.form.name, this.form.code)
      } else if (this.mode === 'invite') {
        response = await acceptStaffInvite(this.form.token, this.form.phone, this.form.password, this.form.name)
      } else if (this.mode === 'reset') {
        await resetPassword(this.form.phone, this.form.code, this.form.password)
        await this.openMode('login')
        this.successMessage = '密码已重置，请使用新密码登录。'
        return
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
      this.errorMessage = this.errorText(error, '操作失败，请检查信息后重试')
    } finally {
      this.submitting = false
    }
  }
}
