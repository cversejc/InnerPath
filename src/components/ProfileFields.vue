<template>
  <div class="profile-fields">
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
          <label class="profile-label" :for="`${idPrefix}-name`">称呼 <span class="required">*</span></label>
          <input
            :id="`${idPrefix}-name`"
            class="profile-input"
            :value="profile.name || ''"
            type="text"
            maxlength="50"
            autocomplete="name"
            placeholder="希望我们如何称呼你"
            :aria-invalid="Boolean(errors.name)"
            :aria-describedby="errors.name ? idPrefix + '-name-error' : undefined"
            @input="setField('name', $event.target.value)"
          >
          <p v-if="errors.name" :id="`${idPrefix}-name-error`" class="profile-error" role="alert">{{ errors.name }}</p>
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
              @click="setField('gender', option.value)"
            >
              <span class="profile-choice-mark">{{ option.mark }}</span>
              <strong>{{ option.label }}</strong>
            </button>
          </div>
          <p v-if="errors.gender" :id="`${idPrefix}-gender-error`" class="profile-error" role="alert">{{ errors.gender }}</p>
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
              @click="setField('calendar_type', option.value)"
            >
              <span class="profile-choice-mark">{{ option.mark }}</span>
              <span>
                <strong>{{ option.label }}</strong>
                <small>{{ option.hint }}</small>
              </span>
            </button>
          </div>
          <p v-if="errors.calendar_type" :id="`${idPrefix}-calendar-type-error`" class="profile-error" role="alert">{{ errors.calendar_type }}</p>
        </fieldset>

        <div class="profile-field">
          <span class="profile-label">出生日期 <span class="required">*</span></span>
          <div class="profile-date-grid">
            <label :for="`${idPrefix}-birth-year`">
              <input
                :id="`${idPrefix}-birth-year`"
                class="profile-input"
                :value="profile.birth_year || ''"
                type="tel"
                inputmode="numeric"
                maxlength="4"
                placeholder="1990"
                :aria-invalid="Boolean(errors.birth_date)"
                :aria-describedby="errors.birth_date ? idPrefix + '-birth-date-error' : undefined"
                @input="setNumberField('birth_year', $event.target.value, 4)"
              >
              <span>年</span>
            </label>
            <label :for="`${idPrefix}-birth-month`">
              <input
                :id="`${idPrefix}-birth-month`"
                class="profile-input"
                :value="profile.birth_month || ''"
                type="tel"
                inputmode="numeric"
                maxlength="2"
                placeholder="01"
                :aria-invalid="Boolean(errors.birth_date)"
                :aria-describedby="errors.birth_date ? idPrefix + '-birth-date-error' : undefined"
                @input="setNumberField('birth_month', $event.target.value, 2)"
              >
              <span>月</span>
            </label>
            <label :for="`${idPrefix}-birth-day`">
              <input
                :id="`${idPrefix}-birth-day`"
                class="profile-input"
                :value="profile.birth_day || ''"
                type="tel"
                inputmode="numeric"
                maxlength="2"
                placeholder="01"
                :aria-invalid="Boolean(errors.birth_date)"
                :aria-describedby="errors.birth_date ? idPrefix + '-birth-date-error' : undefined"
                @input="setNumberField('birth_day', $event.target.value, 2)"
              >
              <span>日</span>
            </label>
          </div>
          <p class="profile-hint">按上方选择的历法填写，年龄会由出生日期自动计算</p>
          <p v-if="errors.birth_date" :id="`${idPrefix}-birth-date-error`" class="profile-error" role="alert">{{ errors.birth_date }}</p>
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
              @click="selectTimePrecision(option.value)"
            >{{ option.label }}</button>
          </div>
          <div v-if="profile.birth_time_precision !== 'unknown'" class="profile-time-grid">
            <label :for="`${idPrefix}-birth-hour`">
              <span>小时</span>
              <input
                :id="`${idPrefix}-birth-hour`"
                class="profile-input"
                :value="profile.birth_hour ?? ''"
                type="tel"
                inputmode="numeric"
                maxlength="2"
                placeholder="08"
                :aria-invalid="Boolean(errors.birth_time)"
                :aria-describedby="errors.birth_time ? idPrefix + '-birth-time-error' : undefined"
                @input="setNumberField('birth_hour', $event.target.value, 2)"
              >
            </label>
            <span class="time-separator">:</span>
            <label :for="`${idPrefix}-birth-minute`">
              <span>分钟</span>
              <input
                :id="`${idPrefix}-birth-minute`"
                class="profile-input"
                :value="profile.birth_minute ?? ''"
                type="tel"
                inputmode="numeric"
                maxlength="2"
                placeholder="30"
                :aria-invalid="Boolean(errors.birth_time)"
                :aria-describedby="errors.birth_time ? idPrefix + '-birth-time-error' : undefined"
                @input="setNumberField('birth_minute', $event.target.value, 2)"
              >
            </label>
          </div>
          <p v-if="errors.birth_time_precision || errors.birth_time" :id="`${idPrefix}-birth-time-error`" class="profile-error" role="alert">{{ errors.birth_time_precision || errors.birth_time }}</p>
        </fieldset>

        <div class="profile-field">
          <label class="profile-label" :for="`${idPrefix}-birth-place`">出生地 <span class="recommended">建议填写</span></label>
          <input
            :id="`${idPrefix}-birth-place`"
            class="profile-input"
            :value="profile.birth_place || ''"
            type="text"
            maxlength="100"
            autocomplete="address-level2"
            placeholder="如：广东省广州市"
            @input="setField('birth_place', $event.target.value)"
          >
          <p class="profile-hint">建议填写到省 / 市；无法提供时仍可继续，但分析精度可能受影响</p>
        </div>
      </div>
    </section>

    <button
      v-if="showOptional && optionalCollapsible"
      type="button"
      class="optional-toggle"
      :aria-expanded="optionalExpanded"
      :aria-controls="`${idPrefix}-optional-section`"
      @click="$emit('update:optionalExpanded', !optionalExpanded)"
    >
      <span>{{ optionalExpanded ? '收起个人画像' : '展开个人画像' }}</span>
      <span class="optional-toggle-meta">{{ optionalExpanded ? '稳定背景，可随时更新' : '还有可选信息' }}</span>
      <span aria-hidden="true">{{ optionalExpanded ? '−' : '+' }}</span>
    </button>

    <section v-if="showOptional && (!optionalCollapsible || optionalExpanded)" :id="`${idPrefix}-optional-section`" class="profile-section profile-section-optional" aria-labelledby="profile-optional-title">
      <div class="profile-section-heading">
        <div>
          <p class="section-kicker">OPTIONAL PORTRAIT</p>
          <h3 id="profile-optional-title">完善个人画像</h3>
        </div>
        <p>选填信息会作为稳定背景复用；当前困惑、关系和身心状态只放在本次申请里</p>
      </div>

      <div class="profile-optional-grid">
        <div class="profile-field">
          <label class="profile-label" :for="`${idPrefix}-residence`">目前居住地 <span class="optional">选填</span></label>
          <input
            :id="`${idPrefix}-residence`"
            class="profile-input"
            :value="profile.current_residence || ''"
            type="text"
            maxlength="100"
            placeholder="如：上海市"
            @input="setField('current_residence', $event.target.value)"
          >
        </div>

        <div class="profile-field">
          <label class="profile-label" :for="`${idPrefix}-marital-status`">婚姻状态 <span class="optional">选填</span></label>
          <select :id="`${idPrefix}-marital-status`" class="profile-input" :value="profile.marital_status || ''" @change="setField('marital_status', $event.target.value || null)">
            <option value="">暂不填写</option>
            <option v-for="option in maritalOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </div>

        <div class="profile-field">
          <label class="profile-label" :for="`${idPrefix}-occupation-status`">目前的职业状态 <span class="optional">选填</span></label>
          <select :id="`${idPrefix}-occupation-status`" class="profile-input" :value="profile.occupation_status || ''" @change="setField('occupation_status', $event.target.value || null)">
            <option value="">暂不填写</option>
            <option v-for="option in occupationOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </div>

        <div class="profile-field">
          <label class="profile-label" :for="`${idPrefix}-education`">最高学历 <span class="optional">选填</span></label>
          <select :id="`${idPrefix}-education`" class="profile-input" :value="profile.highest_education || ''" @change="setField('highest_education', $event.target.value || null)">
            <option value="">暂不填写</option>
            <option v-for="option in educationOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </div>

        <div class="profile-field">
          <label class="profile-label" :for="`${idPrefix}-mbti`">MBTI <span class="optional">选填</span></label>
          <input
            :id="`${idPrefix}-mbti`"
            class="profile-input profile-input-uppercase"
            :value="profile.mbti || ''"
            type="text"
            maxlength="4"
            placeholder="如：INTJ"
            @input="setField('mbti', $event.target.value.toUpperCase().replace(/[^A-Z]/g, '').slice(0, 4))"
          >
        </div>

        <div class="profile-field">
          <label class="profile-label" :for="`${idPrefix}-keywords`">性格关键词 <span class="optional">选填</span></label>
          <input
            :id="`${idPrefix}-keywords`"
            class="profile-input"
            :value="keywordsText"
            type="text"
            maxlength="120"
            placeholder="用逗号分隔，如：独立、敏感、好奇"
            @input="setKeywords($event.target.value)"
          >
          <p class="profile-hint">建议填写 3—5 个关键词</p>
        </div>

        <div class="profile-field profile-field-wide">
          <label class="profile-label" :for="`${idPrefix}-strengths`">当前最大的优势 <span class="optional">选填</span></label>
          <textarea :id="`${idPrefix}-strengths`" class="profile-input profile-textarea" rows="3" maxlength="500" placeholder="你觉得自己最可靠的能力是什么？" :value="profile.strengths || ''" @input="setField('strengths', $event.target.value)"></textarea>
        </div>

        <div class="profile-field profile-field-wide">
          <label class="profile-label" :for="`${idPrefix}-limitations`">当前最大的短板或限制 <span class="optional">选填</span></label>
          <textarea :id="`${idPrefix}-limitations`" class="profile-input profile-textarea" rows="3" maxlength="500" placeholder="哪些事情容易消耗你或限制你的行动？" :value="profile.limitations || ''" @input="setField('limitations', $event.target.value)"></textarea>
        </div>

        <fieldset class="profile-field profile-field-wide profile-choice-fieldset">
          <legend class="profile-label">命理 / 玄学体验 <span class="optional">选填</span></legend>
          <p class="profile-hint">最多选择 3 项</p>
          <div class="profile-check-grid">
            <label v-for="option in experienceOptions" :key="option.value" class="profile-check-card">
              <input type="checkbox" :checked="listIncludes('mingli_experience', option.value)" @change="toggleList('mingli_experience', option.value, 3)">
              <span>{{ option.label }}</span>
            </label>
          </div>
        </fieldset>

        <fieldset class="profile-field profile-choice-fieldset">
          <legend class="profile-label">对命理 / 玄学的态度 <span class="optional">选填</span></legend>
          <div class="profile-radio-stack">
            <label v-for="option in attitudeOptions" :key="option.value" class="profile-radio-card">
              <input type="radio" :name="`${idPrefix}-attitude`" :value="option.value" :checked="profile.mingli_attitude === option.value" @change="setField('mingli_attitude', option.value)">
              <span>{{ option.label }}</span>
            </label>
          </div>
        </fieldset>

        <fieldset class="profile-field profile-choice-fieldset">
          <legend class="profile-label">内容深度偏好 <span class="optional">选填</span></legend>
          <div class="profile-radio-stack">
            <label v-for="option in depthOptions" :key="option.value" class="profile-radio-card">
              <input type="radio" :name="`${idPrefix}-depth`" :value="option.value" :checked="profile.preferred_content_depth === option.value" @change="setField('preferred_content_depth', option.value)">
              <span>{{ option.label }}</span>
            </label>
          </div>
        </fieldset>

        <fieldset class="profile-field profile-field-wide profile-choice-fieldset">
          <legend class="profile-label">希望使用说明书 / 日历的场景 <span class="optional">选填</span></legend>
          <p class="profile-hint">最多选择 6 项</p>
          <div class="profile-check-grid">
            <label v-for="option in usageOptions" :key="option.value" class="profile-check-card">
              <input type="checkbox" :checked="listIncludes('default_usage_scenarios', option.value)" @change="toggleList('default_usage_scenarios', option.value, 6)">
              <span>{{ option.label }}</span>
            </label>
          </div>
        </fieldset>
      </div>
    </section>
  </div>
</template>

<script>
export default {
  name: 'ProfileFields',
  props: {
    modelValue: {
      type: Object,
      required: true
    },
    showOptional: {
      type: Boolean,
      default: false
    },
    optionalCollapsible: {
      type: Boolean,
      default: false
    },
    optionalExpanded: {
      type: Boolean,
      default: true
    },
    errors: {
      type: Object,
      default: () => ({})
    },
    idPrefix: {
      type: String,
      default: 'profile'
    }
  },
  emits: ['update:modelValue', 'update:optionalExpanded'],
  data() {
    return {
      genderOptions: [
        { value: 'male', label: '男', mark: '乾' },
        { value: 'female', label: '女', mark: '坤' }
      ],
      calendarOptions: [
        { value: 'solar', label: '公历', hint: '身份证日期', mark: '日' },
        { value: 'lunar', label: '农历', hint: '传统阴历', mark: '月' }
      ],
      timeOptions: [
        { value: 'unknown', label: '不知道' },
        { value: 'approximate', label: '大概时间' },
        { value: 'exact', label: '精确时间' }
      ],
      maritalOptions: [
        { value: 'single', label: '单身' },
        { value: 'dating', label: '恋爱中' },
        { value: 'married', label: '已婚' },
        { value: 'divorced', label: '离异' },
        { value: 'other', label: '其他' }
      ],
      occupationOptions: [
        { value: 'full_time', label: '全职工作' },
        { value: 'freelance', label: '自由职业' },
        { value: 'entrepreneur', label: '创业者' },
        { value: 'student', label: '学生' },
        { value: 'unemployed', label: '待业' },
        { value: 'job_seeking', label: '求职中' },
        { value: 'other', label: '其他' }
      ],
      educationOptions: [
        { value: 'high_school_or_below', label: '高中及以下' },
        { value: 'college', label: '大专' },
        { value: 'bachelor', label: '本科' },
        { value: 'master', label: '硕士' },
        { value: 'doctorate_or_above', label: '博士及以上' }
      ],
      experienceOptions: [
        { value: 'bazi_ziwei', label: '八字 / 紫微斗数命理咨询' },
        { value: 'astrology', label: '星座 / 星盘分析' },
        { value: 'tarot', label: '塔罗牌占卜' },
        { value: 'ai_divination', label: '在线 AI 占卜 / 命理工具' },
        { value: 'feng_shui', label: '风水咨询' },
        { value: 'never', label: '从未接触过' },
        { value: 'other', label: '其他' }
      ],
      attitudeOptions: [
        { value: 'strongly_believe', label: '非常相信' },
        { value: 'reference', label: '比较相信，作为参考' },
        { value: 'uncertain', label: '半信半疑' },
        { value: 'curious', label: '不太相信，但感兴趣' },
        { value: 'disbelieve', label: '完全不相信' }
      ],
      depthOptions: [
        { value: 'concise', label: '简洁明了，给核心结论即可' },
        { value: 'balanced', label: '中等深度，有解释和背景' },
        { value: 'deep', label: '深入详细，希望了解完整的命理逻辑' }
      ],
      usageOptions: [
        { value: 'morning_planning', label: '每天早上规划一天' },
        { value: 'evening_review', label: '每天晚上复盘反思' },
        { value: 'when_confused', label: '遇到困惑时查找指引' },
        { value: 'before_decision', label: '做重要决策前参考' },
        { value: 'emotional_support', label: '情绪低落时寻求安慰' },
        { value: 'other', label: '其他' }
      ]
    }
  },
  computed: {
    profile() {
      return this.modelValue || {}
    },
    keywordsText() {
      return Array.isArray(this.profile.personality_keywords)
        ? this.profile.personality_keywords.join('、')
        : (this.profile.personality_keywords || '')
    }
  },
  methods: {
    emitProfile(nextProfile) {
      this.$emit('update:modelValue', nextProfile)
    },
    setField(field, value) {
      this.emitProfile({ ...this.profile, [field]: value })
    },
    setNumberField(field, value, maxLength) {
      const digits = String(value || '').replace(/\D/g, '').slice(0, maxLength)
      this.setField(field, digits === '' ? null : Number(digits))
    },
    selectTimePrecision(value) {
      const nextProfile = { ...this.profile, birth_time_precision: value }
      if (value === 'unknown') {
        nextProfile.birth_hour = null
        nextProfile.birth_minute = null
      }
      this.emitProfile(nextProfile)
    },
    setKeywords(value) {
      const keywords = String(value || '')
        .split(/[、,，\s]+/)
        .map(item => item.trim())
        .filter(Boolean)
        .slice(0, 5)
      this.setField('personality_keywords', keywords)
    },
    listIncludes(field, value) {
      return Array.isArray(this.profile[field]) && this.profile[field].includes(value)
    },
    toggleList(field, value, maxItems) {
      const current = Array.isArray(this.profile[field]) ? [...this.profile[field]] : []
      const index = current.indexOf(value)
      if (index >= 0) current.splice(index, 1)
      else if (current.length < maxItems) current.push(value)
      this.setField(field, current)
    }
  }
}
</script>

<style scoped>
.profile-fields {
  display: grid;
  gap: 22px;
}

.profile-section {
  display: grid;
  gap: 24px;
  padding: clamp(18px, 4vw, 30px);
  border: 1px solid rgba(139, 90, 20, .14);
  border-radius: 20px;
  background: rgba(255, 252, 245, .54);
}

.profile-section-optional {
  background: rgba(255, 240, 223, .42);
}

.profile-section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 22px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(139, 90, 20, .12);
}

.profile-section-heading h3 {
  margin-top: 4px;
  color: var(--ink);
  font-size: clamp(22px, 3vw, 30px);
}

.profile-section-heading > p {
  max-width: 360px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.7;
}

.profile-field-stack,
.profile-optional-grid {
  display: grid;
  gap: 22px;
}

.profile-optional-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.profile-field {
  display: grid;
  min-width: 0;
  gap: 9px;
}

.profile-field-wide {
  grid-column: 1 / -1;
}

.profile-label {
  color: var(--ink);
  font-size: 14px;
  font-weight: 800;
}

.required {
  color: var(--cinnabar-deep);
}

.optional,
.recommended {
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
}

.recommended {
  color: var(--gold-deep);
}

.profile-input {
  width: 100%;
  min-height: 48px;
  border: 1px solid rgba(139, 90, 20, .2);
  border-radius: 12px;
  padding: 11px 13px;
  background: rgba(255, 255, 255, .78);
  color: var(--ink);
  font-size: 16px;
  line-height: 1.5;
  transition: border-color .2s ease, box-shadow .2s ease, background .2s ease;
}

.profile-input:focus {
  border-color: var(--cinnabar);
  outline: 0;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(184, 92, 80, .12);
}

.profile-input-uppercase {
  letter-spacing: .14em;
}

.profile-textarea {
  min-height: 96px;
  resize: vertical;
}

.profile-hint {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.6;
}

.profile-error {
  color: var(--cinnabar-deep);
  font-size: 12px;
  line-height: 1.5;
}

.profile-choice-fieldset {
  border: 0;
  padding: 0;
}

.profile-choice-grid {
  display: grid;
  gap: 10px;
}

.profile-choice-grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.profile-choice-grid.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.profile-choice-card {
  display: grid;
  min-height: 74px;
  place-items: center;
  gap: 6px;
  border: 1px solid rgba(139, 90, 20, .18);
  border-radius: 14px;
  padding: 10px 12px;
  background: rgba(255, 250, 240, .64);
  color: var(--ink);
  text-align: center;
  transition: border-color .2s ease, background .2s ease, transform .2s ease;
}

.profile-choice-card:hover {
  border-color: rgba(184, 92, 80, .46);
  transform: translateY(-1px);
}

.profile-choice-card.selected {
  border-color: var(--cinnabar);
  background: rgba(184, 92, 80, .1);
  color: var(--cinnabar-deep);
}

.profile-choice-card.horizontal {
  grid-template-columns: auto 1fr;
  place-items: center start;
  text-align: left;
}

.profile-choice-card.compact {
  min-height: 50px;
  font-weight: 800;
}

.profile-choice-mark {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border: 1px solid rgba(139, 90, 20, .2);
  border-radius: 50%;
  color: var(--gold-deep);
  font-family: var(--font-display);
  font-weight: 800;
}

.profile-choice-card strong {
  font-size: 14px;
}

.profile-choice-card small {
  display: block;
  margin-top: 2px;
  color: var(--muted);
  font-size: 11px;
  font-weight: 500;
}

.profile-date-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr;
  gap: 10px;
}

.profile-date-grid label,
.profile-time-grid label {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 7px;
  min-width: 0;
  color: var(--muted);
  font-size: 13px;
}

.profile-date-grid .profile-input {
  min-width: 0;
}

.profile-time-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: end;
  max-width: 360px;
  gap: 8px;
}

.profile-time-grid label {
  grid-template-columns: 1fr;
  gap: 4px;
}

.time-separator {
  padding-bottom: 12px;
  color: var(--muted);
  font-size: 20px;
}

.profile-check-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.profile-check-card,
.profile-radio-card {
  display: flex;
  min-height: 44px;
  align-items: center;
  gap: 9px;
  border: 1px solid rgba(139, 90, 20, .14);
  border-radius: 11px;
  padding: 8px 10px;
  background: rgba(255, 255, 255, .52);
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.35;
}

.profile-check-card input,
.profile-radio-card input {
  width: 17px;
  height: 17px;
  flex: 0 0 auto;
  accent-color: var(--cinnabar);
}

.profile-radio-stack {
  display: grid;
  gap: 8px;
}

.optional-toggle {
  display: grid;
  grid-template-columns: 1fr auto auto;
  min-height: 48px;
  align-items: center;
  gap: 12px;
  border: 1px solid rgba(139, 90, 20, .14);
  border-radius: 14px;
  padding: 0 14px;
  background: rgba(255, 240, 223, .42);
  color: var(--cinnabar-deep);
  font-size: 14px;
  font-weight: 800;
  text-align: left;
  transition: border-color .2s ease, background .2s ease, transform .2s ease;
}

.optional-toggle:hover {
  border-color: rgba(184, 92, 80, .38);
  background: rgba(255, 240, 223, .68);
  transform: translateY(-1px);
}

.optional-toggle-meta {
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
}

@media (max-width: 640px) {
  .profile-section-heading {
    display: grid;
    gap: 8px;
  }

  .profile-optional-grid,
  .profile-choice-grid.two,
  .profile-check-grid {
    grid-template-columns: 1fr;
  }

  .profile-date-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .profile-date-grid label {
    grid-template-columns: 1fr;
    justify-items: stretch;
    gap: 4px;
  }

  .profile-date-grid label > span {
    text-align: center;
  }

  .optional-toggle {
    grid-template-columns: 1fr auto;
    gap: 8px;
  }

  .optional-toggle-meta {
    grid-column: 1 / -1;
    grid-row: 2;
    margin-top: -12px;
    padding-bottom: 10px;
  }
}
</style>
