<template>
  <div class="auth-page">
    <Transition name="auth-intro">
      <section v-if="showIntro" class="auth-intro" aria-label="辰鉴入场动画">
        <div class="auth-intro-lockup" aria-hidden="true">
          <picture>
            <source srcset="/brand-logo.webp" type="image/webp">
            <img class="auth-intro-logo" src="/brand-logo.png" alt="" width="640" height="640" fetchpriority="high" decoding="async">
          </picture>
        </div>
      </section>
    </Transition>

    <div class="auth-shell" :aria-hidden="showIntro ? 'true' : undefined" :inert="showIntro">
      <header class="auth-topbar">
        <router-link class="auth-logo" to="/" aria-label="辰鉴首页">
          <picture>
            <source srcset="/brand-emblem.webp" type="image/webp">
            <img class="auth-logo-mark" src="/brand-emblem.png" alt="" width="214" height="256" decoding="async">
          </picture>
          <span>辰鉴</span>
        </router-link>
      </header>

      <main class="auth-card">
        <header class="auth-head">
          <h1>{{ title }}</h1>
          <p class="auth-subtitle">{{ subtitle }}</p>
        </header>

        <p v-if="errorMessage" id="auth-error" class="auth-message error" role="alert" aria-live="assertive">{{ errorMessage }}</p>
        <p v-if="successMessage" id="auth-success" class="auth-message success" role="status" aria-live="polite">{{ successMessage }}</p>

        <div id="auth-panel" ref="authPanel" class="auth-panel" role="region" :aria-label="title" tabindex="-1">
          <form class="auth-form" :aria-describedby="errorMessage ? 'auth-error' : undefined" @submit.prevent="submit">
            <div class="auth-fields">
              <label v-if="mode === 'register' || mode === 'invite'" class="auth-field">
                <span>姓名</span>
                <input v-model.trim="form.name" type="text" autocomplete="name" required placeholder="你的称呼">
              </label>

              <label class="auth-field">
                <span>手机号</span>
                <input v-model.trim="form.phone" type="tel" inputmode="numeric" autocomplete="tel" maxlength="11" pattern="[0-9]{11}" required placeholder="请输入手机号">
              </label>

              <label v-if="mode === 'invite'" class="auth-field">
                <span>邀请令牌</span>
                <input v-model.trim="form.token" type="text" autocomplete="one-time-code" required placeholder="粘贴邀请令牌">
              </label>

              <div v-if="requiresCode" class="auth-field">
                <label for="auth-verification-code">短信验证码</label>
                <div class="auth-code-row">
                  <input id="auth-verification-code" v-model.trim="form.code" type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="6" pattern="[0-9]{6}" required placeholder="输入 6 位验证码">
                  <button class="auth-code-button" type="button" :disabled="sendingCode || codeCooldown > 0" @click="sendCode">
                    {{ codeButtonLabel }}
                  </button>
                </div>
              </div>

              <label class="auth-field">
                <span>{{ mode === 'reset' ? '新密码' : mode === 'login' ? '密码' : '设置密码' }}</span>
                <input v-model="form.password" type="password" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" minlength="8" maxlength="128" required :placeholder="mode === 'login' ? '请输入密码' : '至少 8 位密码'">
              </label>

              <label v-if="mode === 'reset'" class="auth-field">
                <span>确认新密码</span>
                <input v-model="form.passwordConfirmation" type="password" autocomplete="new-password" minlength="8" maxlength="128" required placeholder="再次输入新密码">
              </label>
            </div>

            <button class="primary-button full-width auth-submit" type="submit" :disabled="submitting" :aria-busy="submitting">
              {{ submitting ? '请稍候…' : submitLabel }}
            </button>
          </form>

          <nav class="auth-actions" aria-label="账号操作">
            <p v-if="mode === 'login'" class="auth-switch">
              还没有账号？
              <button class="auth-inline-link" type="button" @click="openMode('register')">立即注册</button>
            </p>
            <p v-else-if="mode === 'register'" class="auth-switch">
              已有账号？
              <button class="auth-inline-link" type="button" @click="openMode('login')">立即登录</button>
            </p>
            <button v-else-if="mode === 'invite'" class="auth-inline-link" type="button" @click="openMode('login')">返回登录</button>

            <div class="auth-action-links">
              <button v-if="mode === 'login' || mode === 'register'" class="text-button" type="button" @click="openMode('reset')">忘记密码</button>
              <template v-else-if="mode === 'reset'">
                <button class="text-button" type="button" @click="openMode('login')">返回登录</button>
                <button class="text-button" type="button" @click="openMode('register')">注册</button>
              </template>
            </div>
          </nav>
        </div>
      </main>
    </div>
  </div>
</template>

<script>
import {
  acceptStaffInvite,
  login,
  register,
  resetPassword,
  sendVerificationCode
} from '../utils/authService'
import { setAuthenticatedUser } from '../stores/auth'

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
      return this.mode === 'login'
        ? '您好，欢迎登录辰鉴'
        : this.mode === 'invite'
          ? '接受工作邀请'
          : this.mode === 'reset'
            ? '找回密码'
            : '注册'
    },
    subtitle() {
      if (this.mode === 'invite') return '设置账号后进入工作台'
      if (this.mode === 'register') return '验证手机号后创建账号'
      if (this.mode === 'reset') return '验证手机号后设置新密码'
      return '请使用手机号和密码登录'
    },
    submitLabel() {
      if (this.mode === 'login') return '登录'
      if (this.mode === 'invite') return '完成账号设置'
      if (this.mode === 'reset') return '重置密码'
      return '注册'
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
      if (nextMode !== 'login') this.dismissIntro()
    },
    dismissIntro() {
      if (!this.showIntro) return
      if (this.introTimer) {
        window.clearTimeout(this.introTimer)
        this.introTimer = null
      }
      this.showIntro = false
    },
    setMode(mode) {
      this.mode = mode
      this.errorMessage = ''
      this.successMessage = ''
      this.form.password = ''
      this.form.passwordConfirmation = ''
      this.form.code = ''
    },
    openMode(mode) {
      this.setMode(mode)
      const path = { login: '/auth/login', register: '/auth/register', reset: '/auth/forgot-password' }[mode]
      if (!path) return

      const query = { ...this.$route.query }
      delete query.mode
      delete query.token
      const navigation = this.$router.replace({ path, query }).catch(() => {})
      this.$nextTick(() => this.$refs.authPanel?.focus({ preventScroll: true }))
      return navigation
    },
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
      if (!/^\d{11}$/.test(this.form.phone)) {
        this.errorMessage = '请输入正确的 11 位手机号'
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
        'Invalid phone or password': '手机号或密码错误，请检查后重试',
        'Registration temporarily limited': '注册请求过于频繁，请稍后再试',
        'Too many code requests': '验证码请求过于频繁，请稍后再试',
        'Please wait before requesting another code': '请稍后再重新获取验证码',
        'SMS service is not configured': '验证码发送失败，请稍后重试',
        'Failed to send verification code': '验证码发送失败，请稍后重试',
        'Invalid phone or verification code': '手机号或验证码错误，请检查后重试',
        'Invalid or expired verification code': '验证码错误或已过期，请重新获取'
      }
      return messages[detail] || fallback
    },
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
        const fallback = response.user.role === 'admin' ? '/admin' : response.user.role === 'consultant' ? '/staff' : '/pages/home/home'
        await this.$router.replace(redirect || fallback)
      } catch (error) {
        this.errorMessage = this.errorText(error, '操作失败，请检查信息后重试')
      } finally {
        this.submitting = false
      }
    }
  }
}
</script>

<style scoped>
.auth-page {
  display: grid;
  min-height: 100dvh;
  place-items: center;
  padding: 32px 24px;
  background: var(--paper-soft, #fffaf0);
}

.auth-intro {
  position: fixed;
  z-index: 100;
  inset: 0;
  display: grid;
  overflow: hidden;
  place-items: center;
  padding: max(76px, env(safe-area-inset-top, 0px)) 24px max(64px, env(safe-area-inset-bottom, 0px));
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

.auth-intro-lockup {
  display: grid;
  width: min(100%, 420px, 62dvh);
  aspect-ratio: 1;
  place-items: center;
}

.auth-intro-logo {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  animation: authLogoReveal 780ms var(--ease-out) 80ms both;
}

.auth-intro-leave-active {
  transition: opacity 380ms ease, visibility 380ms ease;
}

.auth-intro-leave-active .auth-intro-lockup {
  opacity: 0;
  transform: translateY(-8px);
  transition: opacity 380ms ease, transform 380ms ease;
}

.auth-intro-leave-to {
  opacity: 0;
  visibility: hidden;
}

@keyframes authIntroFrame {
  from { opacity: 0; transform: scale(0.985); }
  to { opacity: 1; transform: scale(1); }
}

@keyframes authLogoReveal {
  from { opacity: 0; transform: translateY(10px) scale(0.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.auth-shell {
  width: min(100%, 460px);
}

.auth-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: clamp(40px, 8vh, 64px);
}

.auth-logo {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--cinnabar-deep, #9e3f35);
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  line-height: 1;
}

.auth-logo-mark {
  display: block;
  width: auto;
  height: 36px;
  flex: 0 0 auto;
  object-fit: contain;
}

.auth-card {
  width: 100%;
  overflow: visible;
}

.auth-head {
  margin-bottom: 32px;
  text-align: left;
}

.auth-card h1 {
  margin: 0 0 10px;
  color: var(--ink, #2f241b);
  font-family: var(--font-ui);
  font-size: 42px;
  font-weight: 800;
  line-height: 1.2;
}

.auth-subtitle {
  margin: 0;
  color: #8b939b;
  font-size: 16px;
  line-height: 1.65;
}

.auth-panel {
  min-width: 0;
}

.auth-form {
  display: grid;
  gap: 30px;
}

.auth-code-button:focus-visible {
  outline: 2px solid var(--cinnabar, #b5574c);
  outline-offset: 2px;
}

.auth-fields {
  display: grid;
  gap: 22px;
}

.auth-field {
  display: grid;
  min-height: 0;
  grid-template-columns: minmax(0, 1fr);
  gap: 4px;
  padding: 0;
  color: var(--ink, #2f241b);
  font-size: 16px;
  font-weight: 700;
}

.auth-field input {
  width: 100%;
  min-height: 52px;
  border: 0;
  border-bottom: 1px solid rgba(68, 79, 88, 0.16);
  border-radius: 0;
  padding: 8px 0 12px;
  background: transparent;
  color: var(--ink, #2f241b);
  font-size: 18px;
  font-weight: 400;
}

.auth-field input::placeholder {
  color: #aab5bf;
  opacity: 1;
}

.auth-field input:focus-visible {
  border-color: var(--cinnabar, #b5574c);
  outline: none;
  box-shadow: 0 1px 0 var(--cinnabar, #b5574c);
}

.auth-code-row {
  display: flex;
  min-width: 0;
  align-items: end;
  gap: 12px;
}

.auth-code-row input {
  width: auto;
  min-width: 0;
  flex: 1 1 auto;
}

.auth-code-button {
  display: inline-flex;
  min-width: 124px;
  min-height: 48px;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(158, 63, 53, 0.32);
  border-radius: 5px;
  padding: 0 12px;
  background: rgba(255, 255, 255, 0.46);
  color: var(--cinnabar-deep, #9e3f35);
  font-size: 14px;
  font-weight: 700;
  transition: background var(--motion-fast, 150ms) ease, border-color var(--motion-fast, 150ms) ease;
}

.auth-code-button:hover:not(:disabled) {
  border-color: var(--cinnabar-deep, #9e3f35);
  background: rgba(181, 87, 76, 0.08);
}

.auth-code-button:disabled {
  cursor: not-allowed;
  opacity: 0.62;
}

.auth-form button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.auth-submit {
  min-height: 58px;
  border-radius: 999px;
  font-size: 18px;
  font-weight: 700;
}

.auth-help {
  margin: 0;
  padding: 2px 0 0;
  color: var(--muted, #7d6653);
  font-size: 16px;
  line-height: 1.75;
}

.auth-help p {
  margin: 0;
}

.auth-actions {
  display: grid;
  justify-items: center;
  gap: 4px;
  margin-top: 18px;
}

.auth-switch {
  margin: 0;
  color: #888f96;
  font-size: 15px;
  line-height: 1.5;
  text-align: center;
}

.auth-inline-link {
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  padding: 0 3px;
  color: var(--cinnabar-deep, #9e3f35);
  font-size: inherit;
  font-weight: 700;
  vertical-align: middle;
}

.auth-inline-link:hover,
.auth-inline-link:focus-visible {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.auth-action-links {
  display: flex;
  min-height: 40px;
  align-items: center;
  justify-content: center;
  gap: 4px 16px;
}

.text-button {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  padding: 0 8px;
  color: var(--muted, #7d6653);
  font-size: 14px;
  transition: background var(--motion-fast, 150ms) ease, color var(--motion-fast, 150ms) ease;
}

.text-button:hover,
.text-button:focus-visible {
  background: rgba(184, 92, 80, 0.08);
  color: var(--cinnabar-deep, #9e3f35);
}

.auth-message {
  margin: 0 0 20px;
  border-radius: 8px;
  padding: 12px 14px;
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

  .auth-topbar {
    margin-bottom: 32px;
  }

  .auth-head {
    margin-bottom: 24px;
  }

  .auth-card h1 {
    font-size: 36px;
  }

  .auth-form {
    gap: 22px;
  }

  .auth-fields {
    gap: 18px;
  }

  .auth-submit {
    min-height: 54px;
  }
}

@media (max-width: 760px) {
  .auth-page {
    padding: 32px 28px;
  }

  .auth-topbar {
    margin-bottom: clamp(36px, 7vh, 52px);
  }

  .auth-card h1 {
    font-size: 38px;
  }

  .auth-head {
    margin-bottom: 28px;
  }

  .auth-form {
    gap: 26px;
  }

  .auth-fields {
    gap: 20px;
  }
}

@media (max-width: 540px) {
  .auth-intro {
    padding:
      max(68px, env(safe-area-inset-top, 0px))
      max(18px, env(safe-area-inset-right, 0px))
      max(48px, env(safe-area-inset-bottom, 0px))
      max(18px, env(safe-area-inset-left, 0px));
  }

  .auth-intro::before {
    inset: 18px 12px;
  }

  .auth-page {
    place-items: start center;
    padding:
      max(72px, calc(env(safe-area-inset-top, 0px) + 48px))
      max(22px, env(safe-area-inset-right, 0px))
      max(24px, env(safe-area-inset-bottom, 0px))
      max(22px, env(safe-area-inset-left, 0px));
  }

  .auth-topbar {
    margin-bottom: clamp(34px, 6vh, 48px);
  }

  .auth-logo {
    gap: 8px;
    font-size: 20px;
  }

  .auth-logo-mark {
    height: 32px;
  }

  .auth-head {
    margin-bottom: 24px;
  }

  .auth-card h1 {
    margin-bottom: 8px;
    font-size: 32px;
  }

  .auth-subtitle {
    font-size: 15px;
  }

  .auth-field {
    font-size: 15px;
  }

  .auth-field input {
    min-height: 48px;
    font-size: 17px;
  }

  .auth-code-row {
    gap: 8px;
  }

  .auth-code-button {
    min-width: 116px;
    padding: 0 8px;
    font-size: 13px;
  }

  .auth-form {
    gap: 26px;
  }

  .auth-submit {
    min-height: 54px;
    font-size: 17px;
  }

  .auth-actions {
    margin-top: 14px;
  }

  .auth-switch {
    font-size: 14px;
  }

  .auth-help {
    font-size: 15px;
  }

  .auth-message {
    margin-bottom: 16px;
    padding: 10px 12px;
    font-size: 13px;
  }
}

@media (max-height: 680px) {
  .auth-page {
    padding-top: 20px;
    padding-bottom: 20px;
  }

  .auth-topbar {
    margin-bottom: 28px;
  }

  .auth-head {
    margin-bottom: 20px;
  }

  .auth-fields {
    gap: 14px;
  }

  .auth-form {
    gap: 20px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .auth-intro::before,
  .auth-intro-logo {
    animation: none;
  }

  .auth-intro-leave-active,
  .auth-intro-leave-active .auth-intro-lockup {
    transition: none;
  }

  .text-button {
    transition: none;
  }

  .auth-code-button {
    transition: none;
  }
}
</style>
