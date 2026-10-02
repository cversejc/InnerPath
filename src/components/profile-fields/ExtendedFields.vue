<script setup>
import { computed, toRefs } from 'vue'
import {
  Cell as VanCell,
  CellGroup as VanCellGroup,
  Checkbox as VanCheckbox,
  CheckboxGroup as VanCheckboxGroup,
  Field as VanField,
  Radio as VanRadio,
  RadioGroup as VanRadioGroup
} from 'vant'
import OptionPickerField from './OptionPickerField.vue'

const props = defineProps({
  profile: { type: Object, required: true },
  idPrefix: { type: String, required: true },
  maritalOptions: { type: Array, default: () => [] },
  occupationOptions: { type: Array, default: () => [] },
  educationOptions: { type: Array, default: () => [] },
  experienceOptions: { type: Array, default: () => [] },
  attitudeOptions: { type: Array, default: () => [] },
  depthOptions: { type: Array, default: () => [] },
  usageOptions: { type: Array, default: () => [] }
})
const { profile, idPrefix, maritalOptions, occupationOptions, educationOptions, experienceOptions, attitudeOptions, depthOptions, usageOptions } = toRefs(props)
const emit = defineEmits(['set-field', 'set-keywords', 'toggle-list'])
const keywordsText = computed(() => Array.isArray(profile.value.personality_keywords)
  ? profile.value.personality_keywords.join('、')
  : (profile.value.personality_keywords || ''))

function listIncludes(field, value) {
  return Array.isArray(profile.value[field]) && profile.value[field].includes(value)
}
</script>

<template>
  <section :id="idPrefix + '-optional-section'" class="profile-section profile-section-optional" aria-labelledby="profile-optional-title">
    <div class="profile-section-heading">
      <div>
        <p class="section-kicker">OPTIONAL PORTRAIT</p>
        <h3 id="profile-optional-title">完善个人画像</h3>
      </div>
      <p>选填信息会作为稳定背景复用；当前困惑、关系和身心状态只放在本次申请里</p>
    </div>

    <div class="profile-optional-grid">
      <div class="profile-field">
        <label class="profile-label" :for="idPrefix + '-residence'">目前居住地 <span class="optional">选填</span></label>
        <VanField
          :id="idPrefix + '-residence'"
          class="profile-van-field"
          :model-value="profile.current_residence || ''"
          name="current_residence"
          type="text"
          maxlength="100"
          placeholder="如：上海市"
          :border="false"
          @update:model-value="emit('set-field', 'current_residence', $event)"
        />
      </div>

      <OptionPickerField
        :id="idPrefix + '-marital-status'"
        label="婚姻状态"
        :model-value="profile.marital_status || ''"
        :options="maritalOptions"
        @update:model-value="emit('set-field', 'marital_status', $event)"
      />

      <OptionPickerField
        :id="idPrefix + '-occupation-status'"
        label="目前的职业状态"
        :model-value="profile.occupation_status || ''"
        :options="occupationOptions"
        @update:model-value="emit('set-field', 'occupation_status', $event)"
      />

      <OptionPickerField
        :id="idPrefix + '-education'"
        label="最高学历"
        :model-value="profile.highest_education || ''"
        :options="educationOptions"
        @update:model-value="emit('set-field', 'highest_education', $event)"
      />

      <div class="profile-field">
        <label class="profile-label" :for="idPrefix + '-mbti'">MBTI <span class="optional">选填</span></label>
        <VanField
          :id="idPrefix + '-mbti'"
          class="profile-van-field profile-van-field-uppercase"
          :model-value="profile.mbti || ''"
          name="mbti"
          type="text"
          maxlength="4"
          placeholder="如：INTJ"
          :border="false"
          @update:model-value="emit('set-field', 'mbti', String($event).toUpperCase().replace(/[^A-Z]/g, '').slice(0, 4))"
        />
      </div>

      <div class="profile-field">
        <label class="profile-label" :for="idPrefix + '-keywords'">性格关键词 <span class="optional">选填</span></label>
        <VanField
          :id="idPrefix + '-keywords'"
          class="profile-van-field"
          :model-value="keywordsText"
          name="personality_keywords"
          type="text"
          maxlength="120"
          placeholder="用逗号分隔，如：独立、敏感、好奇"
          :border="false"
          @update:model-value="emit('set-keywords', $event)"
        />
        <p class="profile-hint">建议填写 3—5 个关键词</p>
      </div>

      <div class="profile-field profile-field-wide">
        <label class="profile-label" :for="idPrefix + '-strengths'">当前最大的优势 <span class="optional">选填</span></label>
        <VanField
          :id="idPrefix + '-strengths'"
          class="profile-van-field"
          :model-value="profile.strengths || ''"
          name="strengths"
          type="textarea"
          rows="3"
          maxlength="500"
          autosize
          placeholder="你觉得自己最可靠的能力是什么？"
          :border="false"
          @update:model-value="emit('set-field', 'strengths', $event)"
        />
      </div>

      <div class="profile-field profile-field-wide">
        <label class="profile-label" :for="idPrefix + '-limitations'">当前最大的短板或限制 <span class="optional">选填</span></label>
        <VanField
          :id="idPrefix + '-limitations'"
          class="profile-van-field"
          :model-value="profile.limitations || ''"
          name="limitations"
          type="textarea"
          rows="3"
          maxlength="500"
          autosize
          placeholder="哪些事情容易消耗你或限制你的行动？"
          :border="false"
          @update:model-value="emit('set-field', 'limitations', $event)"
        />
      </div>

      <fieldset class="profile-field profile-field-wide profile-choice-fieldset">
        <legend class="profile-label">命理 / 玄学体验 <span class="optional">选填</span></legend>
        <p class="profile-hint">最多选择 3 项</p>
        <VanCheckboxGroup
          :model-value="profile.mingli_experience || []"
          class="profile-option-group"
          aria-label="命理 / 玄学体验"
          :max="3"
          icon-size="18px"
          @update:model-value="emit('set-field', 'mingli_experience', $event)"
        >
          <VanCellGroup inset class="profile-option-cells">
            <VanCell
              v-for="option in experienceOptions"
              :key="option.value"
              :class="{ selected: listIncludes('mingli_experience', option.value) }"
              :title="option.label"
              clickable
              @click="emit('toggle-list', 'mingli_experience', option.value, 3)"
            >
              <template #right-icon>
                <VanCheckbox :name="option.value" @click.stop />
              </template>
            </VanCell>
          </VanCellGroup>
        </VanCheckboxGroup>
      </fieldset>

      <fieldset class="profile-field profile-choice-fieldset">
        <legend class="profile-label">对命理 / 玄学的态度 <span class="optional">选填</span></legend>
        <VanRadioGroup
          :model-value="profile.mingli_attitude || ''"
          class="profile-option-group"
          aria-label="对命理 / 玄学的态度"
          icon-size="18px"
          @update:model-value="emit('set-field', 'mingli_attitude', $event)"
        >
          <VanCellGroup inset class="profile-option-cells">
            <VanCell
              v-for="option in attitudeOptions"
              :key="option.value"
              :class="{ selected: profile.mingli_attitude === option.value }"
              :title="option.label"
              clickable
              @click="emit('set-field', 'mingli_attitude', option.value)"
            >
              <template #right-icon>
                <VanRadio :name="option.value" shape="dot" @click.stop />
              </template>
            </VanCell>
          </VanCellGroup>
        </VanRadioGroup>
      </fieldset>

      <fieldset class="profile-field profile-choice-fieldset">
        <legend class="profile-label">内容深度偏好 <span class="optional">选填</span></legend>
        <VanRadioGroup
          :model-value="profile.preferred_content_depth || ''"
          class="profile-option-group"
          aria-label="内容深度偏好"
          icon-size="18px"
          @update:model-value="emit('set-field', 'preferred_content_depth', $event)"
        >
          <VanCellGroup inset class="profile-option-cells">
            <VanCell
              v-for="option in depthOptions"
              :key="option.value"
              :class="{ selected: profile.preferred_content_depth === option.value }"
              :title="option.label"
              clickable
              @click="emit('set-field', 'preferred_content_depth', option.value)"
            >
              <template #right-icon>
                <VanRadio :name="option.value" shape="dot" @click.stop />
              </template>
            </VanCell>
          </VanCellGroup>
        </VanRadioGroup>
      </fieldset>

      <fieldset class="profile-field profile-field-wide profile-choice-fieldset">
        <legend class="profile-label">希望使用说明书 / 日历的场景 <span class="optional">选填</span></legend>
        <p class="profile-hint">最多选择 6 项</p>
        <VanCheckboxGroup
          :model-value="profile.default_usage_scenarios || []"
          class="profile-option-group"
          aria-label="希望使用说明书 / 日历的场景"
          :max="6"
          icon-size="18px"
          @update:model-value="emit('set-field', 'default_usage_scenarios', $event)"
        >
          <VanCellGroup inset class="profile-option-cells">
            <VanCell
              v-for="option in usageOptions"
              :key="option.value"
              :class="{ selected: listIncludes('default_usage_scenarios', option.value) }"
              :title="option.label"
              clickable
              @click="emit('toggle-list', 'default_usage_scenarios', option.value, 6)"
            >
              <template #right-icon>
                <VanCheckbox :name="option.value" @click.stop />
              </template>
            </VanCell>
          </VanCellGroup>
        </VanCheckboxGroup>
      </fieldset>
    </div>
  </section>
</template>

<style scoped src="./FieldControls.css"></style>
<style scoped src="./ExtendedFields.css"></style>
