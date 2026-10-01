import { resolveAuthMode } from '../presentation.js'

export default {
  setMode(mode) {
    this.mode = mode
    this.errorMessage = ''
    this.successMessage = ''
    this.form.password = ''
    this.form.passwordConfirmation = ''
    this.form.code = ''
  },
  syncRouteMode() {
    this.mode = resolveAuthMode(this.$route.query.mode, this.$route.path)
    this.form.token = this.$route.query.token || ''
    if (this.mode !== 'login') this.dismissIntro()
  },
  openMode(mode) {
    this.setMode(mode)
    const path = {
      login: '/auth/login',
      register: '/auth/register',
      reset: '/auth/forgot-password'
    }[mode]
    if (!path) return

    const query = { ...this.$route.query }
    delete query.mode
    delete query.token
    const navigation = this.$router.replace({ path, query }).catch(() => {})
    this.$nextTick(() => this.$refs.authPanel?.focus({ preventScroll: true }))
    return navigation
  },
  dismissIntro() {
    if (!this.showIntro) return
    if (this.introTimer) {
      window.clearTimeout(this.introTimer)
      this.introTimer = null
    }
    this.showIntro = false
  },
  moveMode(offset) {
    const modes = ['login', 'register', 'reset']
    const currentIndex = modes.indexOf(this.mode)
    const nextMode = modes[(currentIndex + offset + modes.length) % modes.length]
    this.setMode(nextMode)
    this.$nextTick(() => document.getElementById('auth-tab-' + nextMode)?.focus())
  }
}
