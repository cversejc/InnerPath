<template>
  <section id="user-panel-profile" class="content-section" role="tabpanel" aria-labelledby="user-tab-profile" tabindex="0">
    <h3 class="section-title">本人画像</h3>
    <p class="profile-intro">
      这里仅维护你本人的分析资料。每次生成报告时都会保存当时的资料快照，之后更新画像不会改写历史报告。
    </p>
    <form class="profile-form" @submit.prevent="$emit('save-profile')">
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
      <VanButton type="primary" native-type="submit" class="btn-save" :disabled="savingSettings" :aria-busy="savingSettings">
        {{ savingSettings ? '保存中…' : '保存本人画像' }}
      </VanButton>
      <p v-if="settingsError" class="settings-error" role="alert">{{ settingsError }}</p>
    </form>
  </section>
</template>

<script>
import { Button as VanButton } from 'vant'
import ProfileFields from '../../../components/ProfileFields.vue'

export default {
  name: 'ProfileSettingsPanel',
  components: { ProfileFields, VanButton },
  props: {
    settings: { type: Object, required: true },
    optionalProfileExpanded: { type: Boolean, default: false },
    settingsErrors: { type: Object, default: () => ({}) },
    settingsError: { type: String, default: '' },
    savingSettings: { type: Boolean, default: false }
  },
  emits: [
    'update:settings',
    'update:optionalProfileExpanded',
    'save-profile'
  ]
}
</script>

<style scoped>
.profile-intro {
  max-width: 720px;
  margin: -10px 0 28px;
  border-left: 3px solid var(--jade, #6f9f93);
  padding: 4px 0 4px 14px;
  color: var(--ink-soft, #614d3d);
  font-size: var(--text-body-sm, 14px);
  line-height: var(--leading-body, 1.6);
}

.profile-form {
  max-width: 720px;
}

.settings-error {
  margin-top: 10px;
  color: var(--cinnabar-deep, #9e3f35);
  font-size: var(--text-body-sm, 14px);
  line-height: var(--leading-body, 1.6);
}

.btn-save {
  min-height: var(--button-height, 46px);
  margin-top: 16px;
  border: 1px solid var(--cinnabar-deep, #9e3f35);
  border-radius: var(--button-radius, 13px);
  padding: 0 22px;
  background: linear-gradient(145deg, var(--cinnabar, #b5574c), var(--cinnabar-deep, #9e3f35));
  color: var(--paper-soft, #fffaf0);
  font-family: var(--font-ui);
  font-size: var(--text-body-sm, 14px);
  font-weight: var(--weight-medium, 500);
}

@media (max-width: 768px) {
  .profile-intro {
    margin: -4px 0 22px;
    font-size: 16px;
  }

  .profile-form .btn-save {
    position: sticky;
    bottom: calc(68px + var(--safe-bottom, 0px));
    z-index: 5;
    width: 100%;
    box-shadow: 0 8px 20px -14px rgba(47, 36, 27, .82);
  }
}
</style>
