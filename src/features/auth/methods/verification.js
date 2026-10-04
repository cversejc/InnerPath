import { sendVerificationCode } from '../session.js'
import { isValidMobilePhone } from '../validation.js'

export default {
  startCodeCooldown(seconds = 60) {
    if (this.codeTimer) window.clearInterval(this.codeTimer)
    this.codeCooldown = seconds
    this.codeTimer = window.setInterval(() => {
      this.codeCooldown -= 1
      if (this.codeCooldown <= 0) {
        this.codeCooldown = 0
        window.clearInterval(this.codeTimer)
        this.codeTimer = null
      }
    }, 1000)
  },
  async sendCode() {
    this.errorMessage = ''
    this.successMessage = ''
    if (!isValidMobilePhone(this.form.phone)) {
      this.errorMessage = '请输入有效的 11 位手机号'
      return
    }

    const purpose = this.mode === 'register' ? 'register' : 'reset'
    this.sendingCode = true
    try {
      await sendVerificationCode(this.form.phone, purpose)
      this.form.code = ''
      this.startCodeCooldown()
      this.successMessage = purpose === 'register'
        ? '验证码已发送，请注意查收。'
        : '如该手机号已注册，验证码将发送到对应号码。'
    } catch (error) {
      this.errorMessage = this.errorText(error, '验证码发送失败，请稍后重试')
    } finally {
      this.sendingCode = false
    }
  },
  errorText(error, fallback) {
    const detail = error.response?.data?.detail
    const messages = {
      'Password setup required': '该账号尚未设置密码，请联系管理员完成首次密码设置',
      'Phone already registered': '该手机号已注册，请直接登录',
      'Invalid phone or password': '账号或密码不正确，请核对后重试',
      'Registration temporarily limited': '注册请求过于频繁，请稍后再试',
      'Too many code requests': '验证码请求过于频繁，请稍后再试',
      'Please wait before requesting another code': '请稍后再重新获取验证码',
      'SMS service is not configured': '短信服务尚未配置，请联系管理员',
      'Failed to send verification code': '验证码发送失败，请稍后重试',
      'Invalid phone or verification code': '手机号或验证码错误，请检查后重试',
      'Invalid or expired verification code': '验证码错误或已过期，请重新获取'
    }
    return messages[detail] || fallback
  }
}
