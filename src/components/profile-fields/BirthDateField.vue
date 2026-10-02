<script setup>
import { computed, ref } from 'vue'
import { DatePicker as VanDatePicker, Field as VanField, Popup as VanPopup } from 'vant'

const props = defineProps({
  profile: { type: Object, required: true },
  errors: { type: Object, default: () => ({}) },
  idPrefix: { type: String, required: true }
})
const emit = defineEmits(['set-birth-date'])

const showPicker = ref(false)
const pickerValue = ref(['1990', '01', '01'])
const minDate = new Date(1900, 0, 1)
const maxDate = new Date()
const birthDateText = computed(() => {
  const { birth_year: year, birth_month: month, birth_day: day } = props.profile
  if (!year || !month || !day) return ''
  return `${year}年${String(month).padStart(2, '0')}月${String(day).padStart(2, '0')}日`
})

function formatDatePickerOption(type, option) {
  const suffix = { year: '年', month: '月', day: '日' }[type]
  return suffix ? { ...option, text: `${option.text}${suffix}` } : option
}

function openPicker() {
  const now = new Date()
  const fallbackYear = Math.min(1990, now.getFullYear())
  const year = Math.min(Math.max(Number(props.profile.birth_year) || fallbackYear, 1900), now.getFullYear())
  const month = Math.min(Math.max(Number(props.profile.birth_month) || 1, 1), 12)
  const day = Math.min(Math.max(Number(props.profile.birth_day) || 1, 1), 31)

  pickerValue.value = [
    String(year).padStart(4, '0'),
    String(month).padStart(2, '0'),
    String(day).padStart(2, '0')
  ]
  showPicker.value = true
}

function confirmBirthDate({ selectedValues }) {
  const [year, month, day] = selectedValues.map(Number)
  emit('set-birth-date', { year, month, day })
  showPicker.value = false
}
</script>

<template>
  <div class="profile-field">
    <label class="profile-label" :for="idPrefix + '-birth-date'">出生日期 <span class="required">*</span></label>
    <VanField
      :id="idPrefix + '-birth-date'"
      class="profile-van-field profile-date-trigger"
      :model-value="birthDateText"
      name="birth_date"
      readonly
      is-link
      placeholder="请选择出生日期"
      :border="false"
      :error="Boolean(errors.birth_date)"
      :aria-describedby="errors.birth_date ? idPrefix + '-birth-date-error' : undefined"
      aria-haspopup="dialog"
      :aria-expanded="showPicker"
      @click="openPicker"
    />
    <p class="profile-hint">按上方选择的历法填写，年龄会由出生日期自动计算</p>
    <p v-if="errors.birth_date" :id="idPrefix + '-birth-date-error'" class="profile-error" role="alert">{{ errors.birth_date }}</p>
  </div>

  <VanPopup v-model:show="showPicker" position="bottom" round teleport="body">
    <VanDatePicker
      v-model="pickerValue"
      title="选择出生日期"
      :min-date="minDate"
      :max-date="maxDate"
      :columns-type="['year', 'month', 'day']"
      :formatter="formatDatePickerOption"
      @confirm="confirmBirthDate"
      @cancel="showPicker = false"
    />
  </VanPopup>
</template>

<style scoped src="./FieldControls.css"></style>
