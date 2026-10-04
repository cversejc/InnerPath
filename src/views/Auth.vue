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

    <aside class="auth-aside" aria-hidden="true">
      <p class="section-kicker">CHENVIS · PERSONAL INSIGHT</p>
      <h2>见自己，<br />知其序，<br /><span>行其路。</span></h2>
      <p class="auth-aside-copy">在纷繁的生活里，<br />找到属于自己的方向与节奏。</p>
      <p class="auth-aside-note">一份洞察，一段新的开始</p>
    </aside>

    <div class="auth-shell" :aria-hidden="showIntro || legalDocument ? 'true' : undefined" :inert="showIntro || !!legalDocument">
      <header class="auth-topbar">
        <router-link class="auth-logo" to="/" aria-label="辰鉴首页">
          <picture>
            <source srcset="/brand-emblem.webp" type="image/webp">
            <img class="auth-logo-mark" src="/brand-emblem.png" alt="" width="214" height="256" decoding="async">
          </picture>
          <span>辰鉴</span>
        </router-link>
        <span class="auth-brand-note">见自己 · 知其序 · 行其路</span>
      </header>

      <main class="auth-card">
        <header class="auth-head">
          <h1>{{ title }}</h1>
          <p class="auth-subtitle">{{ subtitle }}</p>
        </header>

        <p v-if="errorMessage" id="auth-error" class="auth-message error" role="alert" aria-live="assertive">{{ errorMessage }}</p>
        <p v-if="successMessage" id="auth-success" class="auth-message success" role="status" aria-live="polite">{{ successMessage }}</p>

        <div id="auth-panel" ref="authPanel" class="auth-panel" role="region" :aria-label="title" tabindex="-1">
          <VanForm
            ref="authForm"
            class="auth-form"
            :aria-describedby="errorMessage ? 'auth-error' : undefined"
            show-error
            scroll-to-error
            @submit="submit"
          >
            <div class="auth-fields">
              <VanField
                v-if="mode === 'register' || mode === 'invite'"
                id="auth-name"
                v-model.trim="form.name"
                class="auth-field"
                name="name"
                label="姓名"
                label-align="top"
                autocomplete="name"
                placeholder="你的称呼"
                :rules="nameRules"
                :border="false"
              />

              <VanField
                id="auth-phone"
                v-model.trim="form.phone"
                class="auth-field"
                name="phone"
                type="tel"
                inputmode="numeric"
                label="手机号"
                label-align="top"
                autocomplete="tel"
                maxlength="11"
                placeholder="请输入手机号"
                :rules="phoneRules"
                :border="false"
              />

              <VanField
                v-if="mode === 'invite'"
                id="auth-token"
                v-model.trim="form.token"
                class="auth-field"
                name="token"
                label="邀请令牌"
                label-align="top"
                autocomplete="one-time-code"
                placeholder="粘贴邀请令牌"
                :rules="tokenRules"
                :border="false"
              />

              <div v-if="requiresCode" class="auth-code-field">
                <VanField
                  id="auth-verification-code"
                  v-model.trim="form.code"
                  class="auth-field auth-code-input"
                  name="code"
                  label="短信验证码"
                  label-align="top"
                  inputmode="numeric"
                  autocomplete="one-time-code"
                  maxlength="6"
                  placeholder="输入 6 位验证码"
                  :rules="codeRules"
                  :border="false"
                />
                <VanButton type="default" plain native-type="button" class="auth-code-button" :disabled="sendingCode || codeCooldown > 0" @click="sendCode">
                  {{ codeButtonLabel }}
                </VanButton>
              </div>

              <VanField
                id="auth-password"
                v-model="form.password"
                class="auth-field"
                name="password"
                type="password"
                :label="mode === 'reset' ? '新密码' : mode === 'login' ? '密码' : '设置密码'"
                label-align="top"
                :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
                maxlength="128"
                :placeholder="mode === 'login' ? '请输入密码' : '至少 8 位密码'"
                :rules="passwordRules"
                :border="false"
              />

              <VanField
                v-if="mode === 'reset'"
                id="auth-password-confirmation"
                v-model="form.passwordConfirmation"
                class="auth-field"
                name="passwordConfirmation"
                type="password"
                label="确认新密码"
                label-align="top"
                autocomplete="new-password"
                maxlength="128"
                placeholder="再次输入新密码"
                :rules="passwordConfirmationRules"
                :border="false"
              />
            </div>

            <VanButton type="primary" native-type="submit" class="primary-button full-width auth-submit" :disabled="submitting" :aria-busy="submitting">
              {{ submitting ? '请稍候…' : submitLabel }}
            </VanButton>
          </VanForm>

          <nav class="auth-actions" aria-label="账号操作">
            <p v-if="mode === 'login'" class="auth-switch">
              还没有账号？
              <VanButton type="default" plain native-type="button" class="auth-inline-link" @click="openMode('register')">立即注册</VanButton>
            </p>
            <p v-else-if="mode === 'register'" class="auth-switch">
              已有账号？
              <VanButton type="default" plain native-type="button" class="auth-inline-link" @click="openMode('login')">立即登录</VanButton>
            </p>
            <VanButton v-else-if="mode === 'invite'" type="default" plain native-type="button" class="auth-inline-link" @click="openMode('login')">返回登录</VanButton>

            <div class="auth-action-links">
              <VanButton v-if="mode === 'login' || mode === 'register'" type="default" plain native-type="button" class="text-button" @click="openMode('reset')">忘记密码</VanButton>
              <template v-else-if="mode === 'reset'">
                <VanButton type="default" plain native-type="button" class="text-button" @click="openMode('login')">返回登录</VanButton>
                <VanButton type="default" plain native-type="button" class="text-button" @click="openMode('register')">注册</VanButton>
              </template>
            </div>
          </nav>

          <p v-if="mode === 'login' || mode === 'register' || mode === 'invite'" class="auth-legal">
            {{ mode === 'login' ? '登录即代表您已阅读并同意' : '继续即代表您已阅读并同意' }}
            <VanButton ref="termsLink" class="auth-legal-link" type="default" plain native-type="button" @click="openLegalDocument('terms')">《用户协议》</VanButton>
            <span>与</span>
            <VanButton ref="privacyLink" class="auth-legal-link" type="default" plain native-type="button" @click="openLegalDocument('privacy')">《隐私条款》</VanButton>
          </p>
        </div>
      </main>
    </div>

    <LegalDocumentDialog
      v-if="legalDocument"
      :type="legalDocument"
      @close="closeLegalDocument"
    />
  </div>
</template>

<script src="../features/auth/page.js"></script>

<style scoped src="../features/auth/auth.css"></style>
<style scoped src="../features/auth/auth-responsive.css"></style>
