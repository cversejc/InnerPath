export default {
  setMode(mode) {
    this.mode = mode
    this.errorMessage = ''
    this.successMessage = ''
    this.form.password = ''
  },
  moveMode(offset) {
    const modes = ['login', 'register', 'reset']
    const currentIndex = modes.indexOf(this.mode)
    const nextMode = modes[(currentIndex + offset + modes.length) % modes.length]
    this.setMode(nextMode)
    this.$nextTick(() => document.getElementById('auth-tab-' + nextMode)?.focus())
  }
}
