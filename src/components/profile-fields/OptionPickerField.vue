<script setup>
import { computed, ref } from 'vue'
import { Field as VanField, Picker as VanPicker, Popup as VanPopup } from 'vant'

const props = defineProps({
  id: { type: String, required: true },
  label: { type: String, required: true },
  modelValue: { type: String, default: '' },
  options: { type: Array, default: () => [] }
})
const emit = defineEmits(['update:modelValue'])

const showPicker = ref(false)
const pickerValue = ref([''])
const columns = computed(() => [
  { text: '暂不填写', value: '' },
  ...props.options.map(option => ({ text: option.label, value: option.value }))
])
const selectedLabel = computed(() => {
  return props.options.find(option => option.value === props.modelValue)?.label || ''
})

function openPicker() {
  pickerValue.value = [props.modelValue || '']
  showPicker.value = true
}

function confirmSelection({ selectedValues }) {
  emit('update:modelValue', selectedValues[0] || null)
  showPicker.value = false
}
</script>

<template>
  <div class="profile-field">
    <label class="profile-label" :for="id">{{ label }} <span class="optional">选填</span></label>
    <VanField
      :id="id"
      class="profile-van-field profile-picker-trigger"
      :model-value="selectedLabel"
      readonly
      is-link
      placeholder="暂不填写"
      :border="false"
      aria-haspopup="dialog"
      :aria-expanded="showPicker"
      @click="openPicker"
    />
  </div>

  <VanPopup v-model:show="showPicker" position="bottom" round teleport="body">
    <VanPicker
      v-model="pickerValue"
      :title="label"
      :columns="columns"
      @confirm="confirmSelection"
      @cancel="showPicker = false"
    />
  </VanPopup>
</template>

<style scoped src="./FieldControls.css"></style>
