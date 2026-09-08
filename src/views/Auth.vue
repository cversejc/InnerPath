<template>
  <div class="auth-page">
    <div class="auth-card paper-card">
      <router-link class="auth-logo" to="/">辰鉴</router-link>
      <p class="section-kicker">INNERSEEK ACCOUNT</p>
      <h1>{{ title }}</h1>
      <p class="auth-subtitle">手机号仅作为登录账号，不发送短信验证码。先登录，再进入你的专属说明书与行动空间。</p>

      <div v-if="mode !== 'invite'" class="mode-switch" role="tablist">
        <button :class="{ active: mode === 'login' }" @click="setMode('login')">登录</button>
        <button :class="{ active: mode === 'register' }" @click="setMode('register')">注册</button>
        <button :class="{ active: mode === 'reset' }" @click="setMode('reset')">找回密码</button>
      </div>

      <form v-if="mode !== 'reset'" class="auth-form" @submit.prevent="submit">
        <label v-if="mode === 'register' || mode === 'invite'">
          <span>姓名</span>
          <input v-model.trim="form.name" type="text" autocomplete="name" required placeholder="请输入你的称呼">
        </label>

        <label>
          <span>手机号</span>
          <input v-model.trim="form.phone" type="tel" inputmode="numeric" autocomplete="tel" maxlength="11" required placeholder="11位手机号">
        </label>

        <label v-if="mode === 'invite'">
          <span>邀请令牌</span>
          <input v-model.trim="form.token" type="text" required placeholder="粘贴管理员发来的邀请令牌">
        </label>

        <label v-if="mode === 'login' || mode === 'register' || mode === 'invite'">
          <span>{{ mode === 'login' ? '密码' : '设置密码' }}</span>
          <input v-model="form.password" type="password" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" minlength="8" maxlength="128" required placeholder="至少8位密码">
        </label>

        <button class="primary-button full-width" type="submit" :disabled="submitting">
          {{ submitting ? '处理中…' : submitLabel }}
        </button>
      </form>

      <div v-else class="auth-help">
        <strong>忘记密码怎么办？</strong>
        <p>当前版本不启用短信找回密码。请联系管理员在后台重置密码，重置后即可使用手机号和新密码登录。</p>
        <router-link class="text-button" to="/auth/login">返回登录</router-link>
      </div>

      <p v-if="errorMessage" class="auth-message error">{{ errorMessage }}</p>
      <p v-if="successMessage" class="auth-message success">{{ successMessage }}</p>

      <button v-if="mode === 'login'" class="text-button" type="button" @click="setMode('register')">还没有账号？创建账号</button>
      <button v-if="mode === 'invite'" class="text-button" type="button" @click="setMode('login')">返回普通登录</button>
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
      successMessage: ''
    }
  },
  computed: {
    title() {
      return this.mode === 'login' ? '欢迎回来' : this.mode === 'invite' ? '接受工作邀请' : this.mode === 'reset' ? '重设密码' : '创建你的账号'
    },
    submitLabel() {
      return this.mode === 'login' ? '登录辰鉴' : this.mode === 'invite' ? '完成账号设置' : this.mode === 'reset' ? '重设并登录' : '注册并进入'
    }
  },
  mounted() {
    const queryMode = this.$route.query.mode
    const pathMode = this.$route.path.includes('/register')
      ? 'register'
      : this.$route.path.includes('/forgot-password')
        ? 'reset'
        : this.$route.path.includes('/invite')
          ? 'invite'
          : 'login'
    this.mode = ['login', 'register', 'reset', 'invite'].includes(queryMode) ? queryMode : pathMode
    this.form.token = this.$route.query.token || ''
  },
  methods: {
    setMode(mode) {
      this.mode = mode
      this.errorMessage = ''
      this.successMessage = ''
      this.form.password = ''
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
.auth-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 28px 18px;
  background: radial-gradient(circle at top, rgba(245, 219, 176, 0.35), transparent 52%), #f6efe4;
}

.auth-card {
  width: min(100%, 480px);
  padding: 40px;
}

.auth-logo {
  display: inline-block;
  margin-bottom: 30px;
  color: var(--cinnabar-deep, #8f352f);
  font-family: serif;
  font-size: 28px;
  font-weight: 900;
  text-decoration: none;
}

.auth-card h1 {
  margin: 8px 0 10px;
  color: var(--ink, #2d251e);
  font-size: clamp(30px, 7vw, 44px);
}

.auth-subtitle {
  color: var(--muted, #756a60);
  line-height: 1.7;
}

.mode-switch {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
  margin: 28px 0 22px;
  padding: 4px;
  border: 1px solid rgba(80, 54, 32, 0.12);
  border-radius: 12px;
}

.mode-switch button,
.text-button {
  border: 0;
  background: transparent;
  color: var(--muted, #756a60);
  cursor: pointer;
}

.mode-switch button {
  padding: 10px 6px;
  border-radius: 9px;
}

.mode-switch button.active {
  background: #fffaf0;
  color: var(--cinnabar-deep, #8f352f);
  font-weight: 800;
}

.auth-form {
  display: grid;
  gap: 17px;
  margin-top: 24px;
}

.auth-form label {
  display: grid;
  gap: 7px;
  color: var(--ink-soft, #51463d);
  font-size: 14px;
  font-weight: 700;
}

.auth-form input {
  width: 100%;
  padding: 13px 14px;
  border: 1px solid rgba(80, 54, 32, 0.16);
  border-radius: 10px;
  background: rgba(255, 252, 246, 0.78);
  color: var(--ink, #2d251e);
  font: inherit;
}

.auth-form button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.auth-message {
  margin-top: 16px;
  line-height: 1.6;
}

.auth-message.error { color: #a23b35; }
.auth-message.success { color: #39724e; }

.text-button {
  display: block;
  margin: 22px auto 0;
  padding: 4px;
  text-decoration: underline;
}

@media (max-width: 540px) {
  .auth-card { padding: 28px 22px; }
  .mode-switch { font-size: 13px; }
}
</style>
