<template>
  <div class="auth-page">
    <div class="auth-card paper-card">
      <router-link class="auth-logo" to="/">辰鉴</router-link>
      <h1>{{ title }}</h1>
      <p v-if="mode !== 'reset'" class="auth-subtitle">{{ subtitle }}</p>

      <div v-if="mode !== 'invite'" class="mode-switch" role="tablist" aria-label="认证方式">
        <button id="auth-tab-login" type="button" role="tab" aria-controls="auth-panel" :aria-selected="mode === 'login'" :tabindex="mode === 'login' ? 0 : -1" :class="{ active: mode === 'login' }" @click="setMode('login')" @keydown.left.prevent="moveMode(-1)" @keydown.right.prevent="moveMode(1)">登录</button>
        <button id="auth-tab-register" type="button" role="tab" aria-controls="auth-panel" :aria-selected="mode === 'register'" :tabindex="mode === 'register' ? 0 : -1" :class="{ active: mode === 'register' }" @click="setMode('register')" @keydown.left.prevent="moveMode(-1)" @keydown.right.prevent="moveMode(1)">注册</button>
        <button id="auth-tab-reset" type="button" role="tab" aria-controls="auth-panel" :aria-selected="mode === 'reset'" :tabindex="mode === 'reset' ? 0 : -1" :class="{ active: mode === 'reset' }" @click="setMode('reset')" @keydown.left.prevent="moveMode(-1)" @keydown.right.prevent="moveMode(1)">找回密码</button>
      </div>

      <div id="auth-panel" :role="mode === 'invite' ? 'region' : 'tabpanel'" :aria-labelledby="mode === 'invite' ? undefined : `auth-tab-${mode}`" tabindex="-1">
        <form v-if="mode !== 'reset'" class="auth-form" :aria-describedby="errorMessage ? 'auth-error' : undefined" @submit.prevent="submit">
        <label v-if="mode === 'register' || mode === 'invite'">
          <span>姓名</span>
          <input v-model.trim="form.name" type="text" autocomplete="name" required placeholder="你的称呼">
        </label>

        <label>
          <span>手机号</span>
          <input v-model.trim="form.phone" type="tel" inputmode="numeric" autocomplete="tel" maxlength="11" required placeholder="11位手机号">
        </label>

        <label v-if="mode === 'invite'">
          <span>邀请令牌</span>
          <input v-model.trim="form.token" type="text" autocomplete="one-time-code" required placeholder="粘贴邀请令牌">
        </label>

        <label v-if="mode === 'login' || mode === 'register' || mode === 'invite'">
          <span>{{ mode === 'login' ? '密码' : '设置密码' }}</span>
          <input v-model="form.password" type="password" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" minlength="8" maxlength="128" required placeholder="至少8位密码">
        </label>

        <button class="primary-button full-width" type="submit" :disabled="submitting" :aria-busy="submitting">
          {{ submitting ? '请稍候…' : submitLabel }}
        </button>
        </form>

        <div v-else class="auth-help">
          <strong>忘记密码？</strong>
          <p>请联系辰鉴支持重设密码，再用手机号登录。</p>
          <router-link class="text-button" to="/auth/login">返回登录</router-link>
        </div>
      </div>

      <p v-if="errorMessage" id="auth-error" class="auth-message error" role="alert" aria-live="assertive">{{ errorMessage }}</p>
      <p v-if="successMessage" id="auth-success" class="auth-message success" role="status" aria-live="polite">{{ successMessage }}</p>

      <button v-if="mode === 'login'" class="text-button" type="button" @click="setMode('register')">创建账号</button>
      <button v-if="mode === 'invite'" class="text-button" type="button" @click="setMode('login')">返回登录</button>
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
    subtitle() {
      return this.mode === 'invite' ? '设置账号后进入工作台。' : '进入报告书与决策日历。'
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
    moveMode(offset) {
      const modes = ['login', 'register', 'reset']
      const currentIndex = modes.indexOf(this.mode)
      const nextMode = modes[(currentIndex + offset + modes.length) % modes.length]
      this.setMode(nextMode)
      this.$nextTick(() => document.getElementById(`auth-tab-${nextMode}`)?.focus())
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
  min-height: 100dvh;
  place-items: center;
  padding: 28px 18px;
  background: radial-gradient(circle at top, rgba(245, 219, 176, 0.35), transparent 52%), #f6efe4;
}

.auth-card {
  width: min(100%, 480px);
  padding: 36px;
}

.auth-logo {
  display: inline-block;
  margin-bottom: 20px;
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
  margin: 0;
  color: var(--muted, #7d6653);
  line-height: 1.7;
}

.auth-help {
  margin-top: 16px;
}

.auth-help p {
  margin: 9px 0 0;
  color: var(--muted, #7d6653);
  line-height: 1.6;
}

.mode-switch {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
  margin: 20px 0 18px;
  padding: 4px;
  border: 1px solid rgba(80, 54, 32, 0.12);
  border-radius: 12px;
}

.mode-switch button,
.text-button {
  border: 0;
  background: transparent;
  color: var(--muted, #7d6653);
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
  margin-top: 18px;
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
  margin-bottom: 0;
  line-height: 1.6;
}

.auth-message.error { color: var(--cinnabar-deep, #9e3f35); }
.auth-message.success { color: #39724e; }

.text-button {
  display: block;
  margin: 18px auto 0;
  padding: 4px;
  text-decoration: underline;
}

@media (max-width: 540px) {
  .auth-page {
    padding: 12px 12px calc(12px + var(--safe-bottom, 0px));
  }

  .auth-card {
    width: min(100%, 360px);
    padding: 20px 16px 18px;
    border-radius: 16px;
  }

  .auth-logo {
    margin-bottom: 10px;
    font-size: 24px;
  }

  .auth-card h1 {
    margin-top: 0;
    font-size: clamp(27px, 8vw, 34px);
  }

  .auth-subtitle {
    font-size: 14px;
    line-height: 1.65;
  }

  .mode-switch {
    width: min(100%, 300px);
    margin: 14px 0 12px;
    font-size: 12px;
  }

  .mode-switch button {
    min-height: 44px;
    padding: 8px 3px;
  }

  .auth-form {
    gap: 11px;
    margin-top: 14px;
  }

  .auth-form label {
    gap: 6px;
    font-size: 13px;
  }

  .auth-form input {
    min-height: 46px;
    font-size: 16px;
    padding: 11px 12px;
    border-radius: 12px;
  }

  .auth-form .primary-button {
    width: min(100%, 260px);
    min-height: 46px;
    justify-self: center;
  }

  .text-button {
    margin-top: 14px;
    font-size: 13px;
  }
}

/* 按钮专项：登录页的模式切换保持分段控件，辅助动作保持轻量文字样式。 */
.mode-switch {
  gap: 8px;
}

.mode-switch button {
  min-height: 44px;
  border-radius: 9px;
}

.text-button {
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  padding: 0 8px;
  color: var(--cinnabar-deep, #9e3f35);
  transition: background var(--motion-fast, 150ms) ease, color var(--motion-fast, 150ms) ease;
}

.text-button:hover,
.text-button:focus-visible {
  background: rgba(184, 92, 80, 0.08);
}

.auth-form .primary-button {
  border-radius: var(--button-radius, 13px);
}
</style>
