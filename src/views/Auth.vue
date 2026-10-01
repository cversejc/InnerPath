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

<script src="../features/auth/page.js"></script>

<style scoped src="../features/auth/auth.css"></style>
