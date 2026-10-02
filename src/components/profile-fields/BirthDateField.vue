<script setup>
import { computed, ref } from 'vue'
import {
  DatePicker as VanDatePicker,
  Field as VanField,
  Picker as VanPicker,
  Popup as VanPopup
} from 'vant'
import { getLunarCalendarOptions } from '../../features/users/api.js'

const props = defineProps({
  profile: { type: Object, required: true },
  errors: { type: Object, default: () => ({}) },
  idPrefix: { type: String, required: true }
})
const emit = defineEmits(['set-birth-date'])

const showPicker = ref(false)
const solarPickerValue = ref(['1990', '01', '01'])
const lunarOptions = ref(null)
const lunarColumns = ref([])
const lunarPickerValue = ref([])
const lunarLoading = ref(false)
const pickerError = ref('')
const minDate = new Date(1900, 0, 1)
const maxDate = new Date()
const currentYear = maxDate.getFullYear()
const lunarYearPickerOptions = computed(() => (lunarOptions.value?.years || [])
  .slice()
  .reverse()
  .map(option => ({ text: option.label, value: option.value })))
const birthDateText = computed(() => {
  const { birth_year: year, birth_month: month, birth_day: day } = props.profile
  if (!year || !month || !day) return ''
  if (props.profile.calendar_type === 'lunar') {
    const selectedMonth = lunarOptions.value?.years
      .find(option => option.value === Number(year))
      ?.months.find(option => option.value === (props.profile.birth_is_leap_month ? -Number(month) : Number(month)))
    const monthLabel = selectedMonth?.label
      || `${props.profile.birth_is_leap_month ? '闰' : ''}${month}月`
    return `农历 ${year}年${monthLabel}${lunarDayLabel(Number(day))}`
  }
  return `公历 ${year}年${String(month).padStart(2, '0')}月${String(day).padStart(2, '0')}日`
})

function lunarDayLabel(day) {
  const digits = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九']
  if (day === 10) return '初十'
  if (day < 10) return `初${digits[day]}`
  if (day < 20) return `十${digits[day - 10]}`
  if (day === 20) return '二十'
  if (day < 30) return `廿${digits[day - 20]}`
  return '三十'
}

function formatDatePickerOption(type, option) {
  const suffix = { year: '年', month: '月', day: '日' }[type]
  return suffix ? { ...option, text: `${option.text}${suffix}` } : option
}

function getLunarYearOption(year) {
  return lunarOptions.value?.years.find(option => option.value === Number(year))
}

function setLunarColumns(year, month, day) {
  const yearOption = getLunarYearOption(year)
  const months = yearOption?.months || []
  if (!months.length) return
  const selectedMonth = months.find(option => option.value === Number(month)) || months[0]
  const days = Array.from(
    { length: selectedMonth.max_day },
    (_, index) => ({ text: lunarDayLabel(index + 1), value: index + 1 })
  )
  const selectedDay = Math.min(Math.max(Number(day) || 1, 1), selectedMonth.max_day)
  lunarColumns.value = [
    lunarYearPickerOptions.value,
    months.map(option => ({ text: option.label, value: option.value })),
    days
  ]
  lunarPickerValue.value = [Number(year), selectedMonth.value, selectedDay]
}

function confirmSolarBirthDate({ selectedValues }) {
  const [year, month, day] = selectedValues.map(Number)
  emit('set-birth-date', { year, month, day, birth_is_leap_month: false })
  showPicker.value = false
}

function confirmLunarBirthDate({ selectedValues }) {
  const [year, signedMonth, day] = selectedValues.map(Number)
  emit('set-birth-date', {
    year,
    month: Math.abs(signedMonth),
    day,
    birth_is_leap_month: signedMonth < 0
  })
  showPicker.value = false
}

function handleLunarPickerChange({ selectedValues, columnIndex }) {
  if (columnIndex === 2) return
  setLunarColumns(...selectedValues)
}

async function openPicker() {
  pickerError.value = ''
  if (props.profile.calendar_type !== 'lunar') {
    const fallbackYear = Math.min(1990, currentYear)
    const year = Math.min(Math.max(Number(props.profile.birth_year) || fallbackYear, 1900), currentYear)
    const month = Math.min(Math.max(Number(props.profile.birth_month) || 1, 1), 12)
    const day = Math.min(Math.max(Number(props.profile.birth_day) || 1, 1), 31)

    solarPickerValue.value = [
      String(year).padStart(4, '0'),
      String(month).padStart(2, '0'),
      String(day).padStart(2, '0')
    ]
    showPicker.value = true
    return
  }

  lunarLoading.value = true
  try {
    if (!lunarOptions.value) lunarOptions.value = await getLunarCalendarOptions()
    const fallbackYear = Math.min(1990, lunarOptions.value.max_year)
    const year = Math.min(
      Math.max(Number(props.profile.birth_year) || fallbackYear, 1900),
      lunarOptions.value.max_year
    )
    const signedMonth = props.profile.birth_is_leap_month
      ? -Number(props.profile.birth_month)
      : Number(props.profile.birth_month)
    setLunarColumns(year, signedMonth, props.profile.birth_day)
    showPicker.value = true
  } catch {
    pickerError.value = '农历日期暂时无法加载，请稍后重试。'
  } finally {
    lunarLoading.value = false
  }
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
      :aria-describedby="errors.birth_date ? idPrefix + '-birth-date-error' : pickerError ? idPrefix + '-birth-date-picker-error' : undefined"
      aria-haspopup="dialog"
      :aria-expanded="showPicker"
      @click="openPicker"
    />
    <p class="profile-hint">{{ profile.calendar_type === 'lunar' ? '闰月会在月份列表中单独标注，年龄按对应公历日期计算' : '按上方选择的历法填写，年龄会由出生日期自动计算' }}</p>
    <p v-if="lunarLoading" class="profile-hint" role="status">正在加载农历日期…</p>
    <p v-if="pickerError" :id="idPrefix + '-birth-date-picker-error'" class="profile-error" role="alert">{{ pickerError }}</p>
    <p v-if="errors.birth_date" :id="idPrefix + '-birth-date-error'" class="profile-error" role="alert">{{ errors.birth_date }}</p>
  </div>

  <VanPopup v-model:show="showPicker" position="bottom" round teleport="body">
    <VanDatePicker
      v-if="profile.calendar_type !== 'lunar'"
      v-model="solarPickerValue"
      title="选择公历出生日期"
      :min-date="minDate"
      :max-date="maxDate"
      :columns-type="['year', 'month', 'day']"
      :formatter="formatDatePickerOption"
      @confirm="confirmSolarBirthDate"
      @cancel="showPicker = false"
    />
    <VanPicker
      v-else
      v-model="lunarPickerValue"
      :columns="lunarColumns"
      title="选择农历出生日期"
      @change="handleLunarPickerChange"
      @confirm="confirmLunarBirthDate"
      @cancel="showPicker = false"
    />
  </VanPopup>
</template>

<style scoped src="./FieldControls.css"></style>
