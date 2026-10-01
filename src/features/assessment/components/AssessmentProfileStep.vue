<script setup>
import { ref } from 'vue'
import { Button as VanButton } from 'vant'
import ProfileFields from '../../../components/ProfileFields.vue'

defineProps({
  draftRestored: { type: Boolean, default: false },
  draftStatus: { type: String, default: '' },
  formMessage: { type: String, default: '' },
  hasExistingProfile: { type: Boolean, default: false },
  profileDraft: { type: Object, required: true },
  profileErrorSummary: { type: Array, default: () => [] },
  profileErrors: { type: Object, default: () => ({}) },
  savingProfile: { type: Boolean, default: false },
  showOptionalProfile: { type: Boolean, default: false }
})

const emit = defineEmits(['save-profile', 'update:profile-draft', 'update:show-optional-profile'])
const stepHeading = ref(null)

function focusStepHeading() {
  stepHeading.value?.focus({ preventScroll: true })
}

defineExpose({ focusStepHeading })
</script>

<template>
  <div class="step-content form-panel">
    <div class="step-heading">
      <p class="section-kicker">STEP 01</p>
      <h2 ref="stepHeading" tabindex="-1">{{ hasExistingProfile ? '确认你的个人档案' : '建立你的个人档案' }}</h2>
      <p>{{ hasExistingProfile ? '档案会用于后续报告与日历申请。你可以只修改发生变化的内容。' : '核心资料用于建立命理基础，画像信息先填你愿意分享的部分。' }}</p>
      <div v-if="draftRestored || draftStatus" class="draft-status" role="status" aria-live="polite">
        <span class="draft-status-dot" aria-hidden="true"></span>
        <span>{{ draftRestored ? '已恢复上次未完成的草稿，你可以继续编辑。' : draftStatus }}</span>
      </div>
    </div>

    <form class="assessment-form" novalidate @submit.prevent="emit('save-profile')">
      <ProfileFields
        :model-value="profileDraft"
        id-prefix="assessment-profile"
        :show-optional="showOptionalProfile"
        :errors="profileErrors"
        @update:model-value="emit('update:profile-draft', $event)"
      />

      <VanButton
        native-type="button"
        type="default"
        plain
        class="fold-toggle"
        :aria-expanded="showOptionalProfile"
        @click="emit('update:show-optional-profile', !showOptionalProfile)"
      >
        <span>{{ showOptionalProfile ? '收起个人画像选填项' : '完善个人画像（选填，之后可修改）' }}</span>
        <span aria-hidden="true">{{ showOptionalProfile ? '−' : '+' }}</span>
      </VanButton>

      <div class="privacy-note">
        <span class="privacy-mark" aria-hidden="true">私</span>
        <p>姓名和出生资料只用于你的账户服务。当前困惑、关系和身心状态不会自动写入长期档案。</p>
      </div>

      <div v-if="profileErrorSummary.length" class="error-summary" role="alert" aria-live="assertive">
        <strong>请先检查以下内容</strong>
        <ul><li v-for="error in profileErrorSummary" :key="error">{{ error }}</li></ul>
      </div>
      <p v-if="formMessage" class="form-message" role="alert" aria-live="assertive">{{ formMessage }}</p>
      <div class="form-submit-bar">
        <VanButton type="primary" native-type="submit" class="primary-button full-width" :disabled="savingProfile" :aria-busy="savingProfile">
          {{ savingProfile ? '保存中…' : '保存档案并继续' }}
        </VanButton>
      </div>
    </form>
  </div>
</template>
