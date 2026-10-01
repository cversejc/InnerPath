<script setup>
import { toRefs } from 'vue'

const props = defineProps({
  profile: { type: Object, required: true },
  errors: { type: Object, default: () => ({}) },
  idPrefix: { type: String, required: true },
  genderOptions: { type: Array, default: () => [] },
  calendarOptions: { type: Array, default: () => [] },
  timeOptions: { type: Array, default: () => [] }
})
const { profile, errors, idPrefix, genderOptions, calendarOptions, timeOptions } = toRefs(props)
const emit = defineEmits(['set-field', 'set-number-field', 'select-time-precision'])
</script>

<template>
  <section class="profile-section" aria-labelledby="profile-core-title">
    <div class="profile-section-heading">
      <div>
        <p class="section-kicker">CORE PROFILE</p>
        <h3 id="profile-core-title">建立你的个人档案</h3>
      </div>
      <p>这些资料会被报告与日历复用，之后只需在资料发生变化时更新</p>
    </div>

    <div class="profile-field-stack">
      <div class="profile-field">
        <label class="profile-label" :for="idPrefix + '-name'">称呼 <span class="required">*</span></label>
        <input
          :id="idPrefix + '-name'"
          class="profile-input"
          :value="profile.name || ''"
          type="text"
          maxlength="50"
          autocomplete="name"
          placeholder="希望我们如何称呼你"
          :aria-invalid="Boolean(errors.name)"
          :aria-describedby="errors.name ? idPrefix + '-name-error' : undefined"
          @input="emit('set-field', 'name', $event.target.value)"
        >
        <p v-if="errors.name" :id="idPrefix + '-name-error'" class="profile-error" role="alert">{{ errors.name }}</p>
      </div>

      <fieldset class="profile-field profile-choice-fieldset" :aria-describedby="errors.gender ? idPrefix + '-gender-error' : undefined">
        <legend class="profile-label">性别 <span class="required">*</span></legend>
        <div class="profile-choice-grid two">
          <button
            v-for="option in genderOptions"
            :key="option.value"
            type="button"
            class="profile-choice-card"
            :class="{ selected: profile.gender === option.value }"
            :aria-pressed="profile.gender === option.value"
            :aria-describedby="errors.gender ? idPrefix + '-gender-error' : undefined"
            @click="emit('set-field', 'gender', option.value)"
          >
            <span class="profile-choice-mark">{{ option.mark }}</span>
            <strong>{{ option.label }}</strong>
          </button>
        </div>
        <p v-if="errors.gender" :id="idPrefix + '-gender-error'" class="profile-error" role="alert">{{ errors.gender }}</p>
      </fieldset>

      <fieldset class="profile-field profile-choice-fieldset" :aria-describedby="errors.calendar_type ? idPrefix + '-calendar-type-error' : undefined">
        <legend class="profile-label">历法类型 <span class="required">*</span></legend>
        <div class="profile-choice-grid two">
          <button
            v-for="option in calendarOptions"
            :key="option.value"
            type="button"
            class="profile-choice-card horizontal"
            :class="{ selected: profile.calendar_type === option.value }"
            :aria-pressed="profile.calendar_type === option.value"
            @click="emit('set-field', 'calendar_type', option.value)"
          >
            <span class="profile-choice-mark">{{ option.mark }}</span>
            <span>
              <strong>{{ option.label }}</strong>
              <small>{{ option.hint }}</small>
            </span>
          </button>
        </div>
        <p v-if="errors.calendar_type" :id="idPrefix + '-calendar-type-error'" class="profile-error" role="alert">{{ errors.calendar_type }}</p>
      </fieldset>

      <div class="profile-field">
        <span class="profile-label">出生日期 <span class="required">*</span></span>
        <div class="profile-date-grid">
          <label :for="idPrefix + '-birth-year'">
            <input
              :id="idPrefix + '-birth-year'"
              class="profile-input"
              :value="profile.birth_year || ''"
              type="tel"
              inputmode="numeric"
              maxlength="4"
              placeholder="1990"
              :aria-invalid="Boolean(errors.birth_date)"
              :aria-describedby="errors.birth_date ? idPrefix + '-birth-date-error' : undefined"
              @input="emit('set-number-field', 'birth_year', $event.target.value, 4)"
            >
            <span>年</span>
          </label>
          <label :for="idPrefix + '-birth-month'">
            <input
              :id="idPrefix + '-birth-month'"
              class="profile-input"
              :value="profile.birth_month || ''"
              type="tel"
              inputmode="numeric"
              maxlength="2"
              placeholder="01"
              :aria-invalid="Boolean(errors.birth_date)"
              :aria-describedby="errors.birth_date ? idPrefix + '-birth-date-error' : undefined"
              @input="emit('set-number-field', 'birth_month', $event.target.value, 2)"
            >
            <span>月</span>
          </label>
          <label :for="idPrefix + '-birth-day'">
            <input
              :id="idPrefix + '-birth-day'"
              class="profile-input"
              :value="profile.birth_day || ''"
              type="tel"
              inputmode="numeric"
              maxlength="2"
              placeholder="01"
              :aria-invalid="Boolean(errors.birth_date)"
              :aria-describedby="errors.birth_date ? idPrefix + '-birth-date-error' : undefined"
              @input="emit('set-number-field', 'birth_day', $event.target.value, 2)"
            >
            <span>日</span>
          </label>
        </div>
        <p class="profile-hint">按上方选择的历法填写，年龄会由出生日期自动计算</p>
        <p v-if="errors.birth_date" :id="idPrefix + '-birth-date-error'" class="profile-error" role="alert">{{ errors.birth_date }}</p>
      </div>

      <fieldset class="profile-field profile-choice-fieldset" :aria-describedby="errors.birth_time_precision || errors.birth_time ? idPrefix + '-birth-time-error' : undefined">
        <legend class="profile-label">出生时间准确度 <span class="required">*</span></legend>
          <p class="profile-hint">不知道也可以跳过；有省 / 市级出生地时，分析更容易做真太阳时校正</p>
        <div class="profile-choice-grid three">
          <button
            v-for="option in timeOptions"
            :key="option.value"
            type="button"
            class="profile-choice-card compact"
            :class="{ selected: profile.birth_time_precision === option.value }"
            :aria-pressed="profile.birth_time_precision === option.value"
            :aria-describedby="errors.birth_time_precision || errors.birth_time ? idPrefix + '-birth-time-error' : undefined"
            @click="emit('select-time-precision', option.value)"
          >{{ option.label }}</button>
        </div>
        <div v-if="profile.birth_time_precision !== 'unknown'" class="profile-time-grid">
          <label :for="idPrefix + '-birth-hour'">
            <span>小时</span>
            <input
              :id="idPrefix + '-birth-hour'"
              class="profile-input"
              :value="profile.birth_hour ?? ''"
              type="tel"
              inputmode="numeric"
              maxlength="2"
              placeholder="08"
              :aria-invalid="Boolean(errors.birth_time)"
              :aria-describedby="errors.birth_time ? idPrefix + '-birth-time-error' : undefined"
              @input="emit('set-number-field', 'birth_hour', $event.target.value, 2)"
            >
          </label>
          <span class="time-separator">:</span>
          <label :for="idPrefix + '-birth-minute'">
            <span>分钟</span>
            <input
              :id="idPrefix + '-birth-minute'"
              class="profile-input"
              :value="profile.birth_minute ?? ''"
              type="tel"
              inputmode="numeric"
              maxlength="2"
              placeholder="30"
              :aria-invalid="Boolean(errors.birth_time)"
              :aria-describedby="errors.birth_time ? idPrefix + '-birth-time-error' : undefined"
              @input="emit('set-number-field', 'birth_minute', $event.target.value, 2)"
            >
          </label>
        </div>
        <p v-if="errors.birth_time_precision || errors.birth_time" :id="idPrefix + '-birth-time-error'" class="profile-error" role="alert">{{ errors.birth_time_precision || errors.birth_time }}</p>
      </fieldset>

      <div class="profile-field">
        <label class="profile-label" :for="idPrefix + '-birth-place'">出生地 <span class="recommended">建议填写</span></label>
        <input
          :id="idPrefix + '-birth-place'"
          class="profile-input"
          :value="profile.birth_place || ''"
          type="text"
          maxlength="100"
          autocomplete="address-level2"
          placeholder="如：广东省广州市"
          @input="emit('set-field', 'birth_place', $event.target.value)"
        >
        <p class="profile-hint">建议填写到省 / 市；无法提供时仍可继续，但分析精度可能受影响</p>
      </div>
    </div>
  </section>
</template>

<style scoped src="./FieldControls.css"></style>
<style scoped src="./CoreFields.css"></style>
