<script setup>
import { toRefs } from 'vue'
import {
  Cell as VanCell,
  CellGroup as VanCellGroup,
  Field as VanField,
  Radio as VanRadio,
  RadioGroup as VanRadioGroup
} from 'vant'
import BirthDateField from './BirthDateField.vue'

const props = defineProps({
  profile: { type: Object, required: true },
  errors: { type: Object, default: () => ({}) },
  idPrefix: { type: String, required: true },
  genderOptions: { type: Array, default: () => [] },
  calendarOptions: { type: Array, default: () => [] },
  timeOptions: { type: Array, default: () => [] }
})
const { profile, errors, idPrefix, genderOptions, calendarOptions, timeOptions } = toRefs(props)
const emit = defineEmits(['set-field', 'set-number-field', 'set-birth-date', 'select-time-precision'])
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
        <VanField
          :id="idPrefix + '-name'"
          class="profile-van-field"
          :model-value="profile.name || ''"
          name="name"
          type="text"
          maxlength="50"
          autocomplete="name"
          placeholder="希望我们如何称呼你"
          :border="false"
          :error="Boolean(errors.name)"
          @update:model-value="emit('set-field', 'name', $event)"
        />
        <p v-if="errors.name" :id="idPrefix + '-name-error'" class="profile-error" role="alert">{{ errors.name }}</p>
      </div>

      <fieldset class="profile-field profile-choice-fieldset" :aria-describedby="errors.gender ? idPrefix + '-gender-error' : undefined">
        <legend class="profile-label">性别 <span class="required">*</span></legend>
        <VanRadioGroup
          :model-value="profile.gender"
          class="profile-option-group"
          aria-label="性别"
          icon-size="18px"
          :aria-describedby="errors.gender ? idPrefix + '-gender-error' : undefined"
          @update:model-value="emit('set-field', 'gender', $event)"
        >
          <VanCellGroup inset class="profile-option-cells">
            <VanCell
              v-for="option in genderOptions"
              :key="option.value"
              :class="{ selected: profile.gender === option.value }"
              :title="option.label"
              clickable
              @click="emit('set-field', 'gender', option.value)"
            >
              <template #icon>
                <span class="profile-cell-mark">{{ option.mark }}</span>
              </template>
              <template #right-icon>
                <VanRadio :name="option.value" shape="dot" @click.stop />
              </template>
            </VanCell>
          </VanCellGroup>
        </VanRadioGroup>
        <p v-if="errors.gender" :id="idPrefix + '-gender-error'" class="profile-error" role="alert">{{ errors.gender }}</p>
      </fieldset>

      <fieldset class="profile-field profile-choice-fieldset" :aria-describedby="errors.calendar_type ? idPrefix + '-calendar-type-error' : undefined">
        <legend class="profile-label">历法类型 <span class="required">*</span></legend>
        <VanRadioGroup
          :model-value="profile.calendar_type"
          class="profile-option-group"
          aria-label="历法类型"
          icon-size="18px"
          :aria-describedby="errors.calendar_type ? idPrefix + '-calendar-type-error' : undefined"
          @update:model-value="emit('set-field', 'calendar_type', $event)"
        >
          <VanCellGroup inset class="profile-option-cells">
            <VanCell
              v-for="option in calendarOptions"
              :key="option.value"
              :class="{ selected: profile.calendar_type === option.value }"
              :title="option.label"
              :label="option.hint"
              clickable
              @click="emit('set-field', 'calendar_type', option.value)"
            >
              <template #icon>
                <span class="profile-cell-mark">{{ option.mark }}</span>
              </template>
              <template #right-icon>
                <VanRadio :name="option.value" shape="dot" @click.stop />
              </template>
            </VanCell>
          </VanCellGroup>
        </VanRadioGroup>
        <p v-if="errors.calendar_type" :id="idPrefix + '-calendar-type-error'" class="profile-error" role="alert">{{ errors.calendar_type }}</p>
      </fieldset>

      <BirthDateField
        :profile="profile"
        :errors="errors"
        :id-prefix="idPrefix"
        @set-birth-date="emit('set-birth-date', $event)"
      />

      <fieldset class="profile-field profile-choice-fieldset" :aria-describedby="errors.birth_time_precision || errors.birth_time ? idPrefix + '-birth-time-error' : undefined">
        <legend class="profile-label">出生时间准确度 <span class="required">*</span></legend>
        <p class="profile-hint">不知道也可以跳过；有省 / 市级出生地时，分析更容易做真太阳时校正</p>
        <VanRadioGroup
          :model-value="profile.birth_time_precision"
          class="profile-segmented"
          aria-label="出生时间准确度"
          direction="horizontal"
          icon-size="18px"
          :aria-describedby="errors.birth_time_precision || errors.birth_time ? idPrefix + '-birth-time-error' : undefined"
          @update:model-value="emit('select-time-precision', $event)"
        >
          <VanRadio
            v-for="option in timeOptions"
            :key="option.value"
            :name="option.value"
            :class="{ selected: profile.birth_time_precision === option.value }"
            shape="dot"
            :aria-describedby="errors.birth_time_precision || errors.birth_time ? idPrefix + '-birth-time-error' : undefined"
          >{{ option.label }}</VanRadio>
        </VanRadioGroup>
        <div v-if="profile.birth_time_precision !== 'unknown'" class="profile-time-grid">
          <label :for="idPrefix + '-birth-hour'">
            <span>小时</span>
            <VanField
              :id="idPrefix + '-birth-hour'"
              class="profile-van-field"
              :model-value="profile.birth_hour ?? ''"
              name="birth_hour"
              type="digit"
              inputmode="numeric"
              maxlength="2"
              placeholder="08"
              :border="false"
              :error="Boolean(errors.birth_time)"
              @update:model-value="emit('set-number-field', 'birth_hour', $event, 2)"
            />
          </label>
          <span class="time-separator">:</span>
          <label :for="idPrefix + '-birth-minute'">
            <span>分钟</span>
            <VanField
              :id="idPrefix + '-birth-minute'"
              class="profile-van-field"
              :model-value="profile.birth_minute ?? ''"
              name="birth_minute"
              type="digit"
              inputmode="numeric"
              maxlength="2"
              placeholder="30"
              :border="false"
              :error="Boolean(errors.birth_time)"
              @update:model-value="emit('set-number-field', 'birth_minute', $event, 2)"
            />
          </label>
        </div>
        <p v-if="errors.birth_time_precision || errors.birth_time" :id="idPrefix + '-birth-time-error'" class="profile-error" role="alert">{{ errors.birth_time_precision || errors.birth_time }}</p>
      </fieldset>

      <div class="profile-field">
        <label class="profile-label" :for="idPrefix + '-birth-place'">出生地 <span class="recommended">建议填写</span></label>
        <VanField
          :id="idPrefix + '-birth-place'"
          class="profile-van-field"
          :model-value="profile.birth_place || ''"
          name="birth_place"
          type="text"
          maxlength="100"
          autocomplete="address-level2"
          placeholder="如：广东省广州市"
          :border="false"
          @update:model-value="emit('set-field', 'birth_place', $event)"
        />
        <p class="profile-hint">建议填写到省 / 市；无法提供时仍可继续，但分析精度可能受影响</p>
      </div>
    </div>
  </section>
</template>

<style scoped src="./FieldControls.css"></style>
<style scoped src="./CoreFields.css"></style>
