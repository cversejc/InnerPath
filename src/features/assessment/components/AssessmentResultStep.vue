<script setup>
import { ref } from 'vue'

defineProps({
  isGenerating: { type: Boolean, default: false }
})

const emit = defineEmits(['view-requests'])
const stepHeading = ref(null)

function focusStepHeading() {
  stepHeading.value?.focus({ preventScroll: true })
}

defineExpose({ focusStepHeading })
</script>

<template>
  <div class="step-content form-panel">
    <div v-if="isGenerating" class="generating">
      <div class="loading-compass" aria-hidden="true"></div>
      <h2 ref="stepHeading" tabindex="-1">正在提交报告申请</h2>
      <p>提交后，咨询师会介入处理报告内容。报告交付后，你就可以在这里阅读，并以它为基础生成决策日历。</p>
    </div>

    <div v-else class="result-success">
      <span class="seal-badge">已提交申请</span>
      <h2 ref="stepHeading" tabindex="-1">申请已进入咨询师工作台</h2>
      <p>你可以在“我的申请”查看处理进度。咨询师交付后，报告会出现在“我的报告”中。</p>
      <div class="button-row">
        <button type="button" class="primary-button" @click="emit('view-requests')">查看我的申请</button>
        <router-link class="secondary-button" to="/pages/user/user?tab=reports">我的报告</router-link>
      </div>
    </div>
  </div>
</template>
