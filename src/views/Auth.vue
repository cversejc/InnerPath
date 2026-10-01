<template>
  <div class="auth-page">
    <Transition name="auth-intro" @after-leave="focusAuthPanel">
      <section v-if="showIntro" class="auth-intro" aria-label="辰鉴入场动画">
        <button ref="skipIntroButton" class="auth-intro-skip" type="button" @click="dismissIntro(true)">
          跳过
        </button>
        <div class="auth-intro-lockup" aria-hidden="true">
          <span class="auth-intro-seal">辰</span>
          <strong>辰鉴</strong>
          <span class="auth-intro-rule"></span>
          <small>照见人生时序</small>
        </div>
      </section>
    </Transition>

    <div
      class="auth-card paper-card"
      :aria-hidden="showIntro ? 'true' : undefined"
      :inert="showIntro"
    >
      <router-link class="auth-logo" to="/" aria-label="辰鉴首页">辰鉴</router-link>

      <header class="auth-head">
        <h1>{{ title }}</h1>
        <p v-if="mode !== 'reset'" class="auth-subtitle">{{ subtitle }}</p>
      </header>

      <p v-if="errorMessage" id="auth-error" class="auth-message error" role="alert" aria-live="assertive">{{ errorMessage }}</p>
      <p v-if="successMessage" id="auth-success" class="auth-message success" role="status" aria-live="polite">{{ successMessage }}</p>

      <div id="auth-panel" ref="authPanel" class="auth-panel" role="region" :aria-label="title" tabindex="-1">
        <form v-if="mode !== 'reset'" class="auth-form" :aria-describedby="errorMessage ? 'auth-error' : undefined" @submit.prevent="submit">
          <div class="auth-fields">
            <label v-if="mode === 'register' || mode === 'invite'" class="auth-field">
              <span>姓名</span>
              <input v-model.trim="form.name" type="text" autocomplete="name" required placeholder="你的称呼">
            </label>

            <label class="auth-field">
              <span>手机号</span>
              <input v-model.trim="form.phone" type="tel" inputmode="numeric" autocomplete="tel" maxlength="11" pattern="[0-9]{11}" required placeholder="11位手机号">
            </label>

            <label v-if="mode === 'invite'" class="auth-field">
              <span>邀请令牌</span>
              <input v-model.trim="form.token" type="text" autocomplete="one-time-code" required placeholder="粘贴邀请令牌">
            </label>

            <label v-if="mode === 'login' || mode === 'register' || mode === 'invite'" class="auth-field">
              <span>{{ mode === 'login' ? '密码' : '设置密码' }}</span>
              <input v-model="form.password" type="password" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" minlength="8" maxlength="128" required placeholder="至少8位密码">
            </label>
          </div>

          <button class="primary-button full-width auth-submit" type="submit" :disabled="submitting" :aria-busy="submitting">
            {{ submitting ? '请稍候…' : submitLabel }}
          </button>
        </form>

        <div v-else-if="mode === 'reset'" class="auth-help">
          <strong>忘记密码？</strong>
          <p>请联系辰鉴支持重设密码，再用手机号登录。</p>
        </div>

        <nav class="auth-actions" aria-label="账号操作">
          <button v-if="mode === 'login'" class="auth-alt-button" type="button" @click="openMode('register')">注册</button>
          <button v-else-if="mode === 'register' || mode === 'reset'" class="auth-alt-button" type="button" @click="openMode('login')">已有账号？登录</button>
          <button v-else-if="mode === 'invite'" class="auth-alt-button" type="button" @click="openMode('login')">返回登录</button>
          <div class="auth-action-links">
            <button v-if="mode === 'login' || mode === 'register'" class="text-button" type="button" @click="openMode('reset')">找回密码</button>
            <button v-if="mode === 'reset'" class="text-button" type="button" @click="openMode('register')">注册</button>
          </div>
        </nav>
      </div>
    </div>
  </div>
</template>

<script>
import {
  acceptStaffInvite,
  login,
  register
} from '../utils/authService'
import { setAuthenticatedUser } from '../stores/auth'

export default {
  name: 'Auth',
  data() {
    const reducedMotion = typeof window !== 'undefined'
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const isLoginRoute = this.$route.path.endsWith('/auth/login')

    return {
      mode: 'login',
      form: {
        name: '',
        phone: '',
        password: '',
        token: ''
      },
      submitting: false,
      errorMessage: '',
      successMessage: '',
      showIntro: isLoginRoute && !reducedMotion,
      introTimer: null,
      introSkipped: false
    }
  },
  computed: {
    title() {
      return this.mode === 'login'
        ? '欢迎回来'
        : this.mode === 'invite'
          ? '接受工作邀请'
          : this.mode === 'reset'
            ? '找回密码'
            : '注册辰鉴账号'
    },
    subtitle() {
      if (this.mode === 'invite') return '设置账号后进入工作台。'
      if (this.mode === 'register') return '注册后进入报告书与决策日历。'
      return '进入报告书与决策日历。'
    },
    submitLabel() {
      return this.mode === 'login' ? '登录辰鉴' : this.mode === 'invite' ? '完成账号设置' : '注册并进入'
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
      this.$nextTick(() => {
        this.introTimer = window.setTimeout(() => this.dismissIntro(), 1500)
      })
    } else {
      this.showIntro = false
    }
  },
  beforeUnmount() {
    if (this.introTimer) {
      window.clearTimeout(this.introTimer)
    }
  },
  methods: {
    syncRouteMode() {
      const queryMode = this.$route.query.mode
      const pathMode = this.$route.path.includes('/register')
        ? 'register'
        : this.$route.path.includes('/forgot-password')
          ? 'reset'
          : this.$route.path.includes('/invite')
            ? 'invite'
            : 'login'
      const nextMode = ['login', 'register', 'reset', 'invite'].includes(queryMode) ? queryMode : pathMode
      this.setMode(nextMode)
      this.form.token = this.$route.query.token || ''
    },
    dismissIntro(skipped = false) {
      if (!this.showIntro) return
      if (this.introTimer) {
        window.clearTimeout(this.introTimer)
        this.introTimer = null
      }
      this.introSkipped = skipped
      this.showIntro = false
    },
    focusAuthPanel() {
      if (this.introSkipped) {
        this.$refs.authPanel?.focus({ preventScroll: true })
      }
      this.introSkipped = false
    },
    setMode(mode) {
      this.mode = mode
      this.errorMessage = ''
      this.successMessage = ''
      this.form.password = ''
    },
    openMode(mode) {
      this.setMode(mode)
      const path = { login: '/auth/login', register: '/auth/register', reset: '/auth/forgot-password' }[mode]
      if (path && this.$route.path !== path) {
        const query = { ...this.$route.query }
        delete query.mode
        this.$router.replace({ path, query }).catch(() => {})
      }
    },
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
        const fallback = response.user.role === 'admin' ? '/admin' : response.user.role === 'consultant' ? '/staff' : '/pages/home/home'
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
}
</script>

<style scoped>
.auth-intro {
  position: fixed;
  z-index: 100;
  inset: 0;
  display: grid;
  overflow: hidden;
  padding:
    max(76px, env(safe-area-inset-top))
    max(24px, env(safe-area-inset-right))
    max(64px, env(safe-area-inset-bottom))
    max(24px, env(safe-area-inset-left));
  place-items: center;
  background:
    linear-gradient(90deg, rgba(139, 90, 20, 0.05) 1px, transparent 1px),
    linear-gradient(180deg, rgba(139, 90, 20, 0.04) 1px, transparent 1px),
    linear-gradient(145deg, #fffaf0 0%, #f8f1e6 58%, #ead9bf 100%);
  background-size: 28px 28px, 28px 28px, auto;
}

.auth-intro::before {
  position: absolute;
  inset: 32px;
  border: 1px solid rgba(139, 90, 20, 0.11);
  content: "";
  pointer-events: none;
  animation: authIntroFrame 900ms var(--ease-out) 80ms both;
}

.auth-intro-skip {
  position: fixed;
  z-index: 1;
  top: max(18px, env(safe-area-inset-top));
  left: max(18px, env(safe-area-inset-left));
  display: inline-flex;
  min-width: 64px;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  padding: 0 14px;
  border: 1px solid rgba(139, 90, 20, 0.14);
  border-radius: 12px;
  background: rgba(255, 250, 240, 0.72);
  color: var(--ink-soft, #614d3d);
  font-size: 13px;
  backdrop-filter: blur(10px);
  transition:
    background var(--motion-fast, 150ms) ease,
    border-color var(--motion-fast, 150ms) ease,
    color var(--motion-fast, 150ms) ease;
}

.auth-intro-skip:hover,
.auth-intro-skip:focus-visible {
  border-color: rgba(158, 63, 53, 0.28);
  background: rgba(255, 250, 240, 0.94);
  color: var(--cinnabar-deep, #9e3f35);
}

.auth-intro-lockup {
  display: grid;
  width: min(100%, 320px);
  justify-items: center;
  text-align: center;
}

.auth-intro-seal {
  display: grid;
  width: 72px;
  height: 72px;
  border: 1px solid rgba(255, 250, 240, 0.48);
  border-radius: 50%;
  place-items: center;
  background: var(--cinnabar-deep, #9e3f35);
  box-shadow: 0 22px 48px -30px rgba(84, 48, 25, 0.76);
  color: var(--paper-soft, #fffaf0);
  font-family: var(--font-display);
  font-size: 30px;
  font-weight: 600;
  line-height: 1;
  animation: authIntroSeal 720ms var(--ease-out) 80ms both;
}

.auth-intro-lockup strong {
  margin-top: 20px;
  font-family: var(--font-display);
  font-size: 42px;
  font-weight: 600;
  line-height: 1.1;
  animation: authIntroText 680ms var(--ease-out) 260ms both;
}

.auth-intro-rule {
  width: 42px;
  height: 1px;
  margin-top: 16px;
  background: rgba(139, 90, 20, 0.32);
  animation: authIntroRule 680ms var(--ease-out) 420ms both;
}

.auth-intro-lockup small {
  margin-top: 12px;
  color: var(--muted, #7d6653);
  font-size: 13px;
  font-weight: 600;
  animation: authIntroText 620ms var(--ease-out) 500ms both;
}

.auth-intro-leave-active {
  transition: opacity 380ms ease, visibility 380ms ease;
}

.auth-intro-leave-active .auth-intro-lockup {
  opacity: 0;
  transform: translateY(-8px);
  transition: opacity 380ms ease, transform 380ms ease;
}

.auth-intro-leave-active .auth-intro-skip {
  opacity: 0;
  transition: opacity 220ms ease;
}

.auth-intro-leave-to {
  opacity: 0;
  visibility: hidden;
}

@keyframes authIntroFrame {
  from {
    opacity: 0;
    transform: scale(0.985);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes authIntroSeal {
  from {
    opacity: 0;
    transform: translateY(12px) scale(0.78);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes authIntroText {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes authIntroRule {
  from {
    opacity: 0;
    transform: scaleX(0);
  }
  to {
    opacity: 1;
    transform: scaleX(1);
  }
}

.auth-page {
  display: grid;
  min-height: 100dvh;
  place-items: center;
  padding: 48px 24px;
  background: radial-gradient(circle at 50% 0%, rgba(245, 219, 176, 0.4), transparent 48%);
}

.auth-card {
  width: min(100%, 460px);
  padding: 40px 32px;
}

.auth-logo {
  display: inline-block;
  margin-bottom: 40px;
  color: var(--cinnabar-deep, #9e3f35);
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
}

.auth-head {
  text-align: left;
}

.auth-card h1 {
  margin: 0 0 14px;
  color: var(--ink, #2d251e);
  font-size: 40px;
  line-height: 1.2;
}

.auth-subtitle {
  margin: 0;
  color: var(--muted, #7d6653);
  font-size: 18px;
  line-height: 1.7;
}

.auth-panel {
  min-width: 0;
}

.auth-help {
  display: grid;
  gap: 10px;
  margin-top: 0;
  text-align: center;
}

.auth-help p {
  margin: 0;
  color: var(--muted, #7d6653);
  font-size: 17px;
  line-height: 1.6;
}

.auth-form {
  display: grid;
  gap: 16px;
  margin-top: 0;
}

.auth-fields {
  overflow: hidden;
  border: 1px solid rgba(80, 54, 32, 0.15);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.78);
}

.auth-field {
  display: grid;
  min-height: 68px;
  grid-template-columns: 96px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  color: var(--ink-soft, #51463d);
  font-size: 16px;
  font-weight: 700;
}

.auth-field + .auth-field {
  border-top: 1px solid rgba(80, 54, 32, 0.09);
}

.auth-field input {
  width: 100%;
  min-height: 50px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--ink, #2d251e);
  font-size: 18px;
  font-weight: 400;
}

.auth-field input:focus-visible {
  outline-offset: 1px;
}

.auth-form button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.auth-submit {
  min-height: 58px;
  border-radius: var(--button-radius, 13px);
  font-size: 17px;
}

.auth-alt-button {
  display: inline-flex;
  width: 100%;
  min-height: 58px;
  align-items: center;
  justify-content: center;
  justify-self: center;
  border: 1px solid rgba(80, 54, 32, 0.16);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.76);
  color: var(--cinnabar-deep, #9e3f35);
  font-size: 17px;
  font-weight: 700;
  transition: background var(--motion-fast, 150ms) ease, border-color var(--motion-fast, 150ms) ease;
}

.auth-actions {
  display: grid;
  justify-items: center;
  gap: 8px;
  margin-top: 14px;
}

.auth-action-links {
  display: flex;
  min-height: 40px;
  align-items: center;
  justify-content: center;
  gap: 8px 16px;
}

.text-button {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  padding: 0 10px;
  color: var(--muted, #7d6653);
  font-size: 14px;
  transition: background var(--motion-fast, 150ms) ease, color var(--motion-fast, 150ms) ease;
}

.text-button:hover,
.text-button:focus-visible {
  background: rgba(184, 92, 80, 0.08);
  color: var(--cinnabar-deep, #9e3f35);
}

.auth-alt-button:hover,
.auth-alt-button:focus-visible {
  border-color: rgba(158, 63, 53, 0.32);
  background: rgba(255, 250, 240, 0.96);
}

.auth-message {
  margin: 0 0 16px;
  padding: 12px 14px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.6;
}

.auth-message.error {
  background: rgba(158, 63, 53, 0.09);
  color: var(--cinnabar-deep, #9e3f35);
}

.auth-message.success {
  background: rgba(95, 143, 130, 0.13);
  color: #39724e;
}

@media (min-width: 761px) and (max-height: 800px) {
  .auth-page {
    padding: 24px;
  }

  .auth-card {
    padding: 24px 32px;
  }

  .auth-logo {
    margin-bottom: 24px;
    font-size: 30px;
  }

  .auth-card h1 {
    margin-bottom: 10px;
    font-size: 36px;
  }

  .auth-subtitle {
    font-size: 17px;
  }

  .auth-form {
    gap: 14px;
  }

  .auth-field {
    min-height: 60px;
  }

  .auth-field input {
    min-height: 46px;
    font-size: 18px;
  }

  .auth-submit {
    min-height: 54px;
    font-size: 17px;
  }

  .auth-alt-button {
    min-height: 54px;
    font-size: 17px;
  }
}

@media (max-width: 760px) {
  .auth-page {
    padding: 28px 18px;
  }

  .auth-card {
    width: min(100%, 460px);
    padding: 28px 24px;
  }

  .auth-logo {
    margin-bottom: 30px;
    font-size: 30px;
  }

  .auth-card h1 {
    font-size: 36px;
  }

  .auth-subtitle {
    font-size: 17px;
  }

  .auth-field {
    min-height: 64px;
    grid-template-columns: 88px minmax(0, 1fr);
    padding: 0 16px;
    font-size: 15px;
  }

  .auth-field input {
    font-size: 17px;
  }

  .auth-submit {
    min-height: 56px;
    font-size: 17px;
  }

  .auth-alt-button {
    min-height: 56px;
    font-size: 16px;
  }
}

@media (max-width: 540px) {
  .auth-intro {
    padding:
      max(68px, env(safe-area-inset-top))
      max(18px, env(safe-area-inset-right))
      max(48px, env(safe-area-inset-bottom))
      max(18px, env(safe-area-inset-left));
  }

  .auth-intro::before {
    inset: 18px 12px;
  }

  .auth-intro-skip {
    top: max(12px, env(safe-area-inset-top));
    left: max(12px, env(safe-area-inset-left));
  }

  .auth-intro-seal {
    width: 64px;
    height: 64px;
    font-size: 27px;
  }

  .auth-intro-lockup strong {
    margin-top: 18px;
    font-size: 38px;
  }

  .auth-page {
    padding: 12px 12px calc(12px + var(--safe-bottom, 0px));
  }

  .auth-card {
    width: min(100%, 420px);
    padding: 22px 18px 20px;
    border-radius: 16px;
  }

  .auth-logo {
    margin-bottom: 22px;
    font-size: 27px;
  }

  .auth-head {
    text-align: center;
  }

  .auth-card h1 {
    margin-bottom: 8px;
    font-size: 29px;
  }

  .auth-subtitle {
    font-size: 14px;
    line-height: 1.65;
  }

  .auth-form {
    gap: 14px;
  }

  .auth-fields {
    border-radius: 13px;
  }

  .auth-field {
    min-height: 58px;
    grid-template-columns: 74px minmax(0, 1fr);
    gap: 8px;
    padding: 0 13px;
    font-size: 14px;
  }

  .auth-field input {
    min-height: 48px;
    font-size: 16px;
    padding: 9px 0;
  }

  .auth-submit {
    min-height: 46px;
    font-size: 16px;
  }

  .auth-alt-button {
    width: 100%;
    min-height: 46px;
    border-radius: 12px;
    font-size: 15px;
  }

  .auth-actions {
    gap: 4px;
    margin-top: 10px;
  }

  .text-button {
    min-height: 40px;
    font-size: 13px;
  }

  .auth-help p {
    font-size: 14px;
  }

  .auth-message {
    margin-bottom: 12px;
    padding: 10px 12px;
    font-size: 13px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .auth-alt-button {
    transition: none;
  }

  .text-button {
    transition: none;
  }
}
</style>
