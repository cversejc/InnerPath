<template>
  <section id="user-panel-settings" class="content-section" role="tabpanel" aria-labelledby="user-tab-settings" tabindex="0">
    <h3 class="section-title">账号设置</h3>

    <section class="settings-section account-info-section" aria-labelledby="account-info-title">
      <div class="settings-section-heading">
        <h4 id="account-info-title">登录账号</h4>
        <p>手机号用于登录。更换时需要验证新手机号并输入当前密码。</p>
      </div>
      <div class="current-phone-card">
        <span>当前手机号</span>
        <strong>{{ maskedPhone }}</strong>
      </div>
      <form class="account-form" @submit.prevent="$emit('save-phone-change')">
        <div class="form-group">
          <label for="new-account-phone">新手机号</label>
          <input
            id="new-account-phone"
            :value="phoneChangeForm.newPhone"
            type="tel"
            inputmode="numeric"
            autocomplete="tel"
            maxlength="11"
            required
            @input="updatePhoneChange('newPhone', $event.target.value)"
          >
        </div>
        <div class="form-group">
          <label for="phone-change-code">短信验证码</label>
          <div class="verification-control">
            <input
              id="phone-change-code"
              :value="phoneChangeForm.code"
              type="text"
              inputmode="numeric"
              autocomplete="one-time-code"
              maxlength="6"
              required
              @input="updatePhoneChange('code', $event.target.value)"
            >
            <VanButton
              type="default"
              plain
              native-type="button"
              class="btn-code"
              :disabled="requestingPhoneCode || !phoneChangeForm.newPhone"
              :aria-busy="requestingPhoneCode"
              @click="$emit('request-phone-code')"
            >
              {{ requestingPhoneCode ? '发送中…' : '获取验证码' }}
            </VanButton>
          </div>
        </div>
        <div class="form-group">
          <label for="phone-change-password">当前密码</label>
          <input
            id="phone-change-password"
            :value="phoneChangeForm.currentPassword"
            type="password"
            minlength="8"
            maxlength="128"
            autocomplete="current-password"
            required
            @input="updatePhoneChange('currentPassword', $event.target.value)"
          >
        </div>
        <p v-if="phoneChangeError" class="settings-error" role="alert">{{ phoneChangeError }}</p>
        <p v-if="phoneChangeMessage" class="settings-success" role="status">{{ phoneChangeMessage }}</p>
        <VanButton type="primary" native-type="submit" class="btn-save" :disabled="savingPhoneChange" :aria-busy="savingPhoneChange">
          {{ savingPhoneChange ? '更新中…' : '更新手机号' }}
        </VanButton>
      </form>
    </section>

    <form class="settings-section password-form" @submit.prevent="$emit('save-password')">
      <div class="settings-section-heading">
        <h4>修改密码</h4>
        <p>请使用不与其他网站共用的新密码，并妥善保管。</p>
      </div>
      <div class="form-group">
        <label for="current-password">当前密码</label>
        <input id="current-password" :value="passwordForm.current" type="password" minlength="8" maxlength="128" required autocomplete="current-password" @input="updatePassword('current', $event.target.value)">
      </div>
      <div class="form-group">
        <label for="new-password">新密码</label>
        <input id="new-password" :value="passwordForm.next" type="password" minlength="8" maxlength="128" required autocomplete="new-password" @input="updatePassword('next', $event.target.value)">
      </div>
      <VanButton type="primary" native-type="submit" class="btn-save" :disabled="savingPassword" :aria-busy="savingPassword">
        {{ savingPassword ? '更新中…' : '更新密码' }}
      </VanButton>
    </form>

    <section class="settings-section account-actions" aria-labelledby="account-actions-title">
      <div class="settings-section-heading">
        <h4 id="account-actions-title">当前设备</h4>
        <p>退出当前设备上的辰鉴账号</p>
      </div>
      <VanButton type="default" plain native-type="button" class="btn-logout" :disabled="loggingOut" :aria-busy="loggingOut" @click="$emit('logout')">
        <template #icon><IconMark name="logout" /></template>
        {{ loggingOut ? '退出中…' : '退出登录' }}
      </VanButton>
    </section>

    <section class="settings-section danger-zone" aria-labelledby="deactivate-account-title">
      <div class="settings-section-heading">
        <h4 id="deactivate-account-title">注销账号</h4>
        <p>注销后账号会进入停用状态，你将无法登录。个人资料、报告、申请及相关记录会继续保留，后台仍可查看。</p>
      </div>
      <VanButton type="default" plain native-type="button" class="btn-deactivate" :disabled="deactivating" @click="openDeactivationDialog">
        注销账号
      </VanButton>
    </section>

    <VanDialog
      v-model:show="showDeactivationDialog"
      title="确认注销账号"
      :show-confirm-button="false"
      :show-cancel-button="false"
      :close-on-click-overlay="false"
      class="deactivation-dialog"
    >
      <div class="deactivation-dialog-content">
        <p>注销后账号会停用，并退出所有设备；历史资料仍会保留。请输入当前密码继续。</p>
        <div class="form-group">
          <label for="deactivation-password">当前密码</label>
          <input
            id="deactivation-password"
            v-model="deactivationPassword"
            type="password"
            minlength="8"
            maxlength="128"
            autocomplete="current-password"
            required
            @input="dialogValidationError = ''"
          >
        </div>
        <p v-if="dialogValidationError || deactivationError" class="settings-error" role="alert">
          {{ dialogValidationError || deactivationError }}
        </p>
        <div class="dialog-actions">
          <VanButton type="default" plain native-type="button" :disabled="deactivating" @click="closeDeactivationDialog">再想想</VanButton>
          <VanButton type="danger" native-type="button" :disabled="deactivating" :aria-busy="deactivating" @click="confirmDeactivation">
            {{ deactivating ? '正在注销…' : '确认注销' }}
          </VanButton>
        </div>
      </div>
    </VanDialog>
  </section>
</template>

<script>
import { Button as VanButton, Dialog as VanDialog } from 'vant'

export default {
  name: 'AccountSettingsPanel',
  components: { VanButton, VanDialog },
  props: {
    accountPhone: { type: String, default: '' },
    phoneChangeForm: { type: Object, required: true },
    phoneChangeError: { type: String, default: '' },
    phoneChangeMessage: { type: String, default: '' },
    requestingPhoneCode: { type: Boolean, default: false },
    savingPhoneChange: { type: Boolean, default: false },
    passwordForm: { type: Object, required: true },
    savingPassword: { type: Boolean, default: false },
    loggingOut: { type: Boolean, default: false },
    deactivating: { type: Boolean, default: false },
    deactivationError: { type: String, default: '' }
  },
  emits: [
    'update:phoneChangeForm',
    'update:passwordForm',
    'request-phone-code',
    'save-phone-change',
    'save-password',
    'logout',
    'deactivate-account'
  ],
  data() {
    return {
      showDeactivationDialog: false,
      deactivationPassword: '',
      dialogValidationError: ''
    }
  },
  computed: {
    maskedPhone() {
      const phone = String(this.accountPhone || '')
      return phone.length === 11 ? `${phone.slice(0, 3)}****${phone.slice(-4)}` : phone || '未设置'
    }
  },
  methods: {
    updatePhoneChange(field, value) {
      this.$emit('update:phoneChangeForm', { ...this.phoneChangeForm, [field]: value })
    },
    updatePassword(field, value) {
      this.$emit('update:passwordForm', { ...this.passwordForm, [field]: value })
    },
    openDeactivationDialog() {
      this.dialogValidationError = ''
      this.showDeactivationDialog = true
      this.$nextTick(() => document.getElementById('deactivation-password')?.focus())
    },
    closeDeactivationDialog() {
      if (this.deactivating) return
      this.showDeactivationDialog = false
      this.deactivationPassword = ''
      this.dialogValidationError = ''
    },
    confirmDeactivation() {
      this.dialogValidationError = ''
      if (!this.deactivationPassword) {
        this.dialogValidationError = '请输入当前密码。'
        return
      }
      if (this.deactivationPassword.length < 8) {
        this.dialogValidationError = '当前密码至少需要 8 位。'
        return
      }
      this.$emit('deactivate-account', this.deactivationPassword)
    }
  }
}
</script>

<style scoped src="../styles/settings.css"></style>
