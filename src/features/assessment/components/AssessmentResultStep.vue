<script setup>
import { ref } from 'vue'
import { Button as VanButton } from 'vant'

defineProps({
  genStep: { type: Number, default: 0 },
  isGenerating: { type: Boolean, default: false },
  requestId: { type: Number, default: null }
})

const emit = defineEmits(['view-requests', 'new-application'])
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
      <h2 ref="stepHeading" tabindex="-1">正在提交咨询师报告申请</h2>
      <p>正在保存本次资料与情境快照，并创建咨询师工作流。报告交付后，你可以基于它生成决策日历。</p>
      <div class="generating-steps">
        <div class="gen-step" :class="{ active: genStep >= 1 }">核对本次情境</div>
        <div class="gen-step" :class="{ active: genStep >= 2 }">创建申请记录</div>
        <div class="gen-step" :class="{ active: genStep >= 3 }">等待咨询师接单</div>
      </div>
    </div>

    <div v-else class="result-success">
      <span class="seal-badge">申请已提交</span>
      <h2 ref="stepHeading" tabindex="-1">等待咨询师接单</h2>
      <p>本次申请已保存完整情境和档案版本。咨询师接单后会开始审核，你可以在“我的申请”查看进度。</p>
      <div class="result-preview paper-card request-confirmation">
        <span>申请编号</span>
        <strong>#{{ requestId }}</strong>
        <span>当前状态</span>
        <strong>等待咨询师接单</strong>
      </div>
      <div class="button-row">
        <VanButton type="primary" native-type="button" class="primary-button" @click="emit('view-requests')">我的申请</VanButton>
        <VanButton type="default" native-type="button" class="secondary-button" @click="emit('new-application')">提交另一份申请</VanButton>
      </div>
    </div>
  </div>
</template>
