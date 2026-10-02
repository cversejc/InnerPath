import { Button as VanButton, Field as VanField, Form as VanForm } from 'vant'
import authModeMethods from './methods/mode.js'
import authSessionMethods from './methods/session.js'
import authVerificationMethods from './methods/verification.js'
import {
  authSubmitLabel,
  authSubtitle,
  authTitle
} from './presentation.js'

export default {
  name: 'Auth',
  components: { VanButton, VanField, VanForm },
  data() {
    const isLoginRoute = this.$route.path === '/auth/login' && (!this.$route.query.mode || this.$route.query.mode === 'login')
    const reducedMotion = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

    return {
      mode: 'login',
      form: {
        name: '',
        phone: '',
        password: '',
        passwordConfirmation: '',
        code: '',
        token: ''
      },
      submitting: false,
      sendingCode: false,
      codeCooldown: 0,
      codeTimer: null,
      errorMessage: '',
      successMessage: '',
      showIntro: isLoginRoute && !reducedMotion,
      introTimer: null
    }
  },
  computed: {
    nameRules() {
      return [{ required: true, message: '请输入你的称呼' }]
    },
    phoneRules() {
      return [
        { required: true, message: '请输入手机号' },
        { pattern: /^[0-9]{11}$/, message: '请输入 11 位手机号' }
      ]
    },
    tokenRules() {
      return [{ required: true, message: '请输入邀请令牌' }]
    },
    codeRules() {
      return [
        { required: true, message: '请输入短信验证码' },
        { pattern: /^[0-9]{6}$/, message: '请输入 6 位验证码' }
      ]
    },
    passwordRules() {
      return [
        { required: true, message: '请输入密码' },
        { validator: value => String(value).length >= 8, message: '密码至少为 8 位' }
      ]
    },
    passwordConfirmationRules() {
      return [
        { required: true, message: '请再次输入新密码' },
        { validator: value => String(value).length >= 8, message: '密码至少为 8 位' },
        { validator: value => value === this.form.password, message: '两次输入的新密码不一致' }
      ]
    },
    title() {
      return authTitle(this.mode)
    },
    subtitle() {
      return authSubtitle(this.mode)
    },
    submitLabel() {
      return authSubmitLabel(this.mode)
    },
    requiresCode() {
      return this.mode === 'register' || this.mode === 'reset'
    },
    codeButtonLabel() {
      if (this.sendingCode) return '发送中…'
      return this.codeCooldown > 0 ? `${this.codeCooldown} 秒后重发` : '获取验证码'
    }
  },
  watch: {
    '$route.fullPath'() {
      this.syncRouteMode()
      this.$nextTick(() => this.$refs.authForm?.resetValidation())
    }
  },
  mounted() {
    this.syncRouteMode()
    if (this.showIntro && this.mode === 'login') {
      this.introTimer = window.setTimeout(() => this.dismissIntro(), 1500)
    } else {
      this.showIntro = false
    }
  },
  beforeUnmount() {
    if (this.introTimer) window.clearTimeout(this.introTimer)
    if (this.codeTimer) window.clearInterval(this.codeTimer)
  },
  methods: {
    ...authModeMethods,
    ...authVerificationMethods,
    ...authSessionMethods
  }
}
