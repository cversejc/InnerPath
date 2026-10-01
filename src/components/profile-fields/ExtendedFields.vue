<script setup>
import { computed, toRefs } from 'vue'

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
      <p>选填信息会作为稳定背景复用；当前困惑、关系和身心状态只放在本次申请里。</p>
    </div>

    <div class="profile-optional-grid">
      <div class="profile-field">
        <label class="profile-label" :for="idPrefix + '-residence'">目前居住地 <span class="optional">选填</span></label>
        <input
          :id="idPrefix + '-residence'"
          class="profile-input"
          :value="profile.current_residence || ''"
          type="text"
          maxlength="100"
          placeholder="如：上海市"
          @input="emit('set-field', 'current_residence', $event.target.value)"
        >
      </div>

      <div class="profile-field">
        <label class="profile-label" :for="idPrefix + '-marital-status'">婚姻状态 <span class="optional">选填</span></label>
        <select :id="idPrefix + '-marital-status'" class="profile-input" :value="profile.marital_status || ''" @change="emit('set-field', 'marital_status', $event.target.value || null)">
          <option value="">暂不填写</option>
          <option v-for="option in maritalOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
      </div>

      <div class="profile-field">
        <label class="profile-label" :for="idPrefix + '-occupation-status'">目前的职业状态 <span class="optional">选填</span></label>
        <select :id="idPrefix + '-occupation-status'" class="profile-input" :value="profile.occupation_status || ''" @change="emit('set-field', 'occupation_status', $event.target.value || null)">
          <option value="">暂不填写</option>
          <option v-for="option in occupationOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
      </div>

      <div class="profile-field">
        <label class="profile-label" :for="idPrefix + '-education'">最高学历 <span class="optional">选填</span></label>
        <select :id="idPrefix + '-education'" class="profile-input" :value="profile.highest_education || ''" @change="emit('set-field', 'highest_education', $event.target.value || null)">
          <option value="">暂不填写</option>
          <option v-for="option in educationOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
      </div>

      <div class="profile-field">
        <label class="profile-label" :for="idPrefix + '-mbti'">MBTI <span class="optional">选填</span></label>
        <input
          :id="idPrefix + '-mbti'"
          class="profile-input profile-input-uppercase"
          :value="profile.mbti || ''"
          type="text"
          maxlength="4"
          placeholder="如：INTJ"
          @input="emit('set-field', 'mbti', $event.target.value.toUpperCase().replace(/[^A-Z]/g, '').slice(0, 4))"
        >
      </div>

      <div class="profile-field">
        <label class="profile-label" :for="idPrefix + '-keywords'">性格关键词 <span class="optional">选填</span></label>
        <input
          :id="idPrefix + '-keywords'"
          class="profile-input"
          :value="keywordsText"
          type="text"
          maxlength="120"
          placeholder="用逗号分隔，如：独立、敏感、好奇"
          @input="emit('set-keywords', $event.target.value)"
        >
        <p class="profile-hint">建议填写 3—5 个关键词。</p>
      </div>

      <div class="profile-field profile-field-wide">
        <label class="profile-label" :for="idPrefix + '-strengths'">当前最大的优势 <span class="optional">选填</span></label>
        <textarea :id="idPrefix + '-strengths'" class="profile-input profile-textarea" rows="3" maxlength="500" placeholder="你觉得自己最可靠的能力是什么？" :value="profile.strengths || ''" @input="emit('set-field', 'strengths', $event.target.value)"></textarea>
      </div>

      <div class="profile-field profile-field-wide">
        <label class="profile-label" :for="idPrefix + '-limitations'">当前最大的短板或限制 <span class="optional">选填</span></label>
        <textarea :id="idPrefix + '-limitations'" class="profile-input profile-textarea" rows="3" maxlength="500" placeholder="哪些事情容易消耗你或限制你的行动？" :value="profile.limitations || ''" @input="emit('set-field', 'limitations', $event.target.value)"></textarea>
      </div>

      <fieldset class="profile-field profile-field-wide profile-choice-fieldset">
        <legend class="profile-label">命理 / 玄学体验 <span class="optional">选填</span></legend>
        <p class="profile-hint">最多选择 3 项。</p>
        <div class="profile-check-grid">
          <label v-for="option in experienceOptions" :key="option.value" class="profile-check-card">
            <input type="checkbox" :checked="listIncludes('mingli_experience', option.value)" @change="emit('toggle-list', 'mingli_experience', option.value, 3)">
            <span>{{ option.label }}</span>
          </label>
        </div>
      </fieldset>

      <fieldset class="profile-field profile-choice-fieldset">
        <legend class="profile-label">对命理 / 玄学的态度 <span class="optional">选填</span></legend>
        <div class="profile-radio-stack">
          <label v-for="option in attitudeOptions" :key="option.value" class="profile-radio-card">
            <input type="radio" :name="idPrefix + '-attitude'" :value="option.value" :checked="profile.mingli_attitude === option.value" @change="emit('set-field', 'mingli_attitude', option.value)">
            <span>{{ option.label }}</span>
          </label>
        </div>
      </fieldset>

      <fieldset class="profile-field profile-choice-fieldset">
        <legend class="profile-label">内容深度偏好 <span class="optional">选填</span></legend>
        <div class="profile-radio-stack">
          <label v-for="option in depthOptions" :key="option.value" class="profile-radio-card">
            <input type="radio" :name="idPrefix + '-depth'" :value="option.value" :checked="profile.preferred_content_depth === option.value" @change="emit('set-field', 'preferred_content_depth', option.value)">
            <span>{{ option.label }}</span>
          </label>
        </div>
      </fieldset>

      <fieldset class="profile-field profile-field-wide profile-choice-fieldset">
        <legend class="profile-label">希望使用说明书 / 日历的场景 <span class="optional">选填</span></legend>
        <p class="profile-hint">最多选择 6 项。</p>
        <div class="profile-check-grid">
          <label v-for="option in usageOptions" :key="option.value" class="profile-check-card">
            <input type="checkbox" :checked="listIncludes('default_usage_scenarios', option.value)" @change="emit('toggle-list', 'default_usage_scenarios', option.value, 6)">
            <span>{{ option.label }}</span>
          </label>
        </div>
      </fieldset>
    </div>
  </section>
</template>

<style scoped src="./FieldControls.css"></style>
<style scoped src="./ExtendedFields.css"></style>
