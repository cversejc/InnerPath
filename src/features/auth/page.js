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
