<template>
  <section id="user-panel-settings" class="content-section" role="tabpanel" aria-labelledby="user-tab-settings" tabindex="0">
    <h3 class="section-title">个人档案与账户设置</h3>
    <form class="settings-form" @submit.prevent="$emit('save-settings')">
      <ProfileFields
        :model-value="settings"
        id-prefix="user-profile"
        :show-optional="true"
        :optional-collapsible="true"
        :optional-expanded="optionalProfileExpanded"
        :errors="settingsErrors"
        @update:model-value="$emit('update:settings', $event)"
        @update:optional-expanded="$emit('update:optionalProfileExpanded', $event)"
      />
      <div class="form-group account-contact-field">
        <label for="user-contact">账户联系方式</label>
        <input id="user-contact" :value="settings.contact" type="tel" autocomplete="tel" readonly>
        <p class="form-hint">联系方式由账户系统管理，不会发送给报告分析模型。</p>
      </div>
      <button type="submit" class="btn-save" :disabled="savingSettings" :aria-busy="savingSettings">{{ savingSettings ? '保存中…' : '保存个人档案' }}</button>
      <p v-if="settingsError" class="settings-error" role="alert">{{ settingsError }}</p>
    </form>
    <form class="password-form" @submit.prevent="$emit('save-password')">
      <h4>修改密码</h4>
      <div class="form-group">
        <label for="current-password">当前密码</label>
        <input id="current-password" :value="passwordForm.current" type="password" minlength="8" maxlength="128" required autocomplete="current-password" @input="updatePassword('current', $event.target.value)">
      </div>
      <div class="form-group">
        <label for="new-password">新密码</label>
        <input id="new-password" :value="passwordForm.next" type="password" minlength="8" maxlength="128" required autocomplete="new-password" @input="updatePassword('next', $event.target.value)">
      </div>
      <button type="submit" class="btn-save" :disabled="savingPassword" :aria-busy="savingPassword">{{ savingPassword ? '更新中…' : '更新密码' }}</button>
    </form>
    <section class="account-actions" aria-labelledby="account-actions-title">
      <div>
        <h4 id="account-actions-title">账号操作</h4>
        <p>退出当前设备上的辰鉴账号。</p>
      </div>
      <button type="button" class="btn-logout" :disabled="loggingOut" :aria-busy="loggingOut" @click="$emit('logout')">
        <IconMark name="logout" />
        {{ loggingOut ? '退出中…' : '退出登录' }}
      </button>
    </section>
  </section>
</template>

<script>
import ProfileFields from '../../../components/ProfileFields.vue'

export default {
  name: 'AccountSettingsPanel',
  components: { ProfileFields },
  props: {
    settings: { type: Object, required: true },
    optionalProfileExpanded: { type: Boolean, default: false },
    settingsErrors: { type: Object, default: () => ({}) },
    settingsError: { type: String, default: '' },
    passwordForm: { type: Object, required: true },
    savingSettings: { type: Boolean, default: false },
    savingPassword: { type: Boolean, default: false },
    loggingOut: { type: Boolean, default: false }
  },
  emits: [
    'update:settings',
    'update:optionalProfileExpanded',
    'update:passwordForm',
    'save-settings',
    'save-password',
    'logout'
  ],
  methods: {
    updatePassword(field, value) {
      this.$emit('update:passwordForm', { ...this.passwordForm, [field]: value })
    }
  }
}
</script>

<style scoped src="../styles/settings.css"></style>
