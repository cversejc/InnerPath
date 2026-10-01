<script setup>
import { ref } from 'vue'
import { Button as VanButton } from 'vant'

defineProps({
  genStep: { type: Number, default: 0 },
  isGenerating: { type: Boolean, default: false },
  reportPreview: { type: Object, required: true }
})

const emit = defineEmits(['go-to-calendar', 'view-report'])
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
      <h2 ref="stepHeading" tabindex="-1">正在为你生成专属报告</h2>
      <p>你的个人特质、当下处境与关注的议题，正在汇成一张更清晰的自我地图。</p>
      <div class="generating-steps">
        <div class="gen-step" :class="{ active: genStep >= 1 }">认识你的起点</div>
        <div class="gen-step" :class="{ active: genStep >= 2 }">看见你的特质</div>
        <div class="gen-step" :class="{ active: genStep >= 3 }">找到重复模式</div>
        <div class="gen-step" :class="{ active: genStep >= 4 }">获得下一步提示</div>
      </div>
    </div>

    <div v-else class="result-success">
      <span class="seal-badge">已生成</span>
      <h2 ref="stepHeading" tabindex="-1">你的人生说明书已经完成</h2>
      <p>这份报告保留了提交时的资料快照。之后更新档案，不会改变这份历史报告。</p>
      <div class="result-preview paper-card">
        <div><span>个人属性</span><strong>{{ reportPreview.energyType }}</strong></div>
        <div><span>核心特质</span><strong>{{ reportPreview.coreTraits }}</strong></div>
        <div><span>行动提示</span><strong>{{ reportPreview.talents }}</strong></div>
      </div>
      <div class="button-row">
        <VanButton type="primary" native-type="button" class="primary-button" @click="emit('view-report')">查看报告</VanButton>
        <VanButton type="default" native-type="button" class="secondary-button" @click="emit('go-to-calendar')">打开决策日历</VanButton>
      </div>
    </div>
  </div>
</template>
