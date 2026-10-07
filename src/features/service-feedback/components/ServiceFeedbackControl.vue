<script setup>
import { reactive, ref } from 'vue'
import { Button as VanButton } from 'vant'
import { submitServiceFeedback } from '../api.js'
import { FEEDBACK_STATUS_LABELS } from '../../../utils/displayLabels.js'

const props = defineProps({
  serviceType: { type: String, required: true },
  sourceId: { type: Number, required: true },
  existing: { type: Object, default: null },
  enabled: { type: Boolean, default: true }
})

const emit = defineEmits(['submitted'])
const open = ref(false)
const showExisting = ref(false)
const submitting = ref(false)
const error = ref('')
const draft = reactive({ feedback_type: 'SUGGESTION', rating: null, comment: '' })
const ratingOptions = [1, 2, 3, 4, 5]
const feedbackTypes = [
  { value: 'SUGGESTION', label: '建议' },
  { value: 'COMPLAINT', label: '投诉' },
  { value: 'PRAISE', label: '表扬' }
]

function feedbackStatusLabel(value) {
  const label = FEEDBACK_STATUS_LABELS[value]
  return value === 'NEW' && label ? `已提交 · ${label}` : label || '已提交反馈'
}

async function submit() {
  if (submitting.value) return
  error.value = ''
  if (draft.comment.trim().length < 5) {
    error.value = '请至少填写 5 个字。'
    return
  }
  submitting.value = true
  try {
    const payload = {
      feedback_type: draft.feedback_type,
      rating: draft.rating,
      comment: draft.comment.trim(),
      ...(props.serviceType === 'report'
        ? { service_request_id: props.sourceId }
        : { calendar_request_id: props.sourceId })
    }
    const saved = await submitServiceFeedback(payload)
    emit('submitted', saved)
    open.value = false
  } catch (requestError) {
    const detail = requestError.response?.data?.detail
    error.value = detail === 'feedback_already_submitted'
      ? '这项服务已有反馈记录，请刷新后查看。'
      : detail === 'feedback_target_not_delivered'
        ? '服务尚未完成，暂时不能提交反馈。'
        : detail || '反馈暂时无法提交，请稍后重试。'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="service-feedback-control">
    <template v-if="existing">
      <button
        class="service-feedback-existing"
        type="button"
        :aria-expanded="showExisting"
        @click="showExisting = !showExisting"
      >
        {{ feedbackStatusLabel(existing.status) }}
      </button>
      <div v-if="showExisting" class="service-feedback-summary">
        <span>{{ feedbackTypes.find(item => item.value === existing.feedback_type)?.label || '反馈' }}</span>
        <span v-if="existing.rating">评分 {{ existing.rating }} / 5</span>
        <p>{{ existing.comment }}</p>
        <p v-if="existing.resolution" class="service-feedback-resolution">处理说明：{{ existing.resolution }}</p>
      </div>
    </template>
    <template v-else-if="enabled">
      <VanButton
        type="default"
        plain
        native-type="button"
        class="service-feedback-open"
        :aria-expanded="open"
        @click="open = !open; error = ''"
      >
        {{ open ? '收起反馈' : '提交服务反馈' }}
      </VanButton>
      <form v-if="open" class="service-feedback-form" @submit.prevent="submit">
        <label>
          反馈类型
          <select v-model="draft.feedback_type">
            <option v-for="item in feedbackTypes" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </label>
        <fieldset>
          <legend>服务评分（选填）</legend>
          <div class="service-feedback-ratings">
            <label v-for="rating in ratingOptions" :key="rating" :class="{ selected: draft.rating === rating }">
              <input v-model="draft.rating" type="radio" :name="`feedback-${serviceType}-${sourceId}`" :value="rating">
              <span>{{ rating }}</span>
            </label>
          </div>
        </fieldset>
        <label>
          反馈内容
          <textarea v-model="draft.comment" minlength="5" maxlength="2000" rows="3" required placeholder="请描述你遇到的情况或希望改进的地方。"></textarea>
        </label>
        <small class="service-feedback-privacy">请避免填写身份证号、联系方式等敏感信息。</small>
        <p v-if="error" class="service-feedback-error" role="alert">{{ error }}</p>
        <div class="service-feedback-actions">
          <VanButton type="default" plain native-type="button" @click="open = false">取消</VanButton>
          <VanButton type="primary" native-type="submit" :loading="submitting" :disabled="submitting">提交</VanButton>
        </div>
      </form>
    </template>
    <p v-else class="service-feedback-unavailable" role="status">反馈状态暂时无法读取。</p>
  </div>
</template>

<style scoped src="../styles/control.css"></style>
