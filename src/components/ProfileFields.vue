<template>
  <div class="profile-fields">
    <section class="profile-section" aria-labelledby="profile-core-title">
      <div class="profile-section-heading">
        <div>
          <p class="section-kicker">CORE PROFILE</p>
          <h3 id="profile-core-title">建立你的个人档案</h3>
        </div>
        <p>这些资料会被报告与日历复用。之后只需在资料发生变化时更新。</p>
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
          <p class="profile-hint">按上方选择的历法填写，年龄会由出生日期自动计算。</p>
          <p v-if="errors.birth_date" :id="`${idPrefix}-birth-date-error`" class="profile-error" role="alert">{{ errors.birth_date }}</p>
        </div>

        <fieldset class="profile-field profile-choice-fieldset" :aria-describedby="errors.birth_time_precision || errors.birth_time ? idPrefix + '-birth-time-error' : undefined">
          <legend class="profile-label">出生时间准确度 <span class="required">*</span></legend>
          <p class="profile-hint">不知道也可以跳过；有省 / 市级出生地时，分析更容易做真太阳时校正。</p>
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
          <p class="profile-hint">建议填写到省 / 市；无法提供时仍可继续，但分析精度可能受影响。</p>
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
        <p>选填信息会作为稳定背景复用；当前困惑、关系和身心状态只放在本次申请里。</p>
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
          <p class="profile-hint">建议填写 3—5 个关键词。</p>
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
          <p class="profile-hint">最多选择 3 项。</p>
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
          <p class="profile-hint">最多选择 6 项。</p>
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

<script src="./ProfileFields.js"></script>

<style scoped src="./ProfileFields.css"></style>
