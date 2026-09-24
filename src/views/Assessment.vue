<template>
  <div class="page-shell assessment">
    <BrandNav />

    <section class="page-header">
      <div class="container header-inner">
        <p class="section-kicker">FI / YOUR LIFE MANUAL</p>
        <h1>申请你的人生说明书</h1>
        <p>从个人属性、能量通路与人生时序出发，提交申请后由咨询师完成 AI 初稿审校与最终交付。</p>
      </div>
    </section>

    <section class="section-band assessment-section">
      <div class="container assessment-container">
        <div class="progress-card paper-card">
          <div class="progress-step" :class="{ active: currentStep >= 1, completed: currentStep > 1 }">
            <span>1</span>
            <p>出生信息</p>
          </div>
          <div class="progress-line" :class="{ active: currentStep > 1 }"></div>
          <div class="progress-step" :class="{ active: currentStep >= 2, completed: currentStep > 2 }">
            <span>2</span>
            <p>当下处境</p>
          </div>
          <div class="progress-line" :class="{ active: currentStep > 2 }"></div>
          <div class="progress-step" :class="{ active: currentStep >= 3 }">
            <span>3</span>
            <p>提交申请</p>
          </div>
        </div>

        <div v-if="currentStep === 1" class="step-content form-panel">
          <div class="step-heading">
            <p class="section-kicker">STEP 01</p>
            <h2 ref="stepHeading" tabindex="-1">填写出生信息</h2>
            <p>出生信息用于建立你的先天坐标；它不是给人生下结论，而是帮助我们找到观察自己的入口。</p>
          </div>

          <form class="assessment-form" :aria-describedby="formMessage ? 'assessment-step-error' : undefined">
            <fieldset class="form-group choice-fieldset">
              <legend class="form-label">性别 <span class="required">*</span></legend>
              <div class="choice-grid two">
                <button
                  type="button"
                  class="choice-card"
                  :class="{ selected: formData.gender === 'male' }"
                  :aria-pressed="formData.gender === 'male'"
                  @click="formData.gender = 'male'"
                >
                  <span>乾</span>
                  <strong>男</strong>
                </button>
                <button
                  type="button"
                  class="choice-card"
                  :class="{ selected: formData.gender === 'female' }"
                  :aria-pressed="formData.gender === 'female'"
                  @click="formData.gender = 'female'"
                >
                  <span>坤</span>
                  <strong>女</strong>
                </button>
              </div>
              <p v-if="fieldErrors.gender" class="field-error" role="alert">{{ fieldErrors.gender }}</p>
            </fieldset>

            <fieldset class="form-group choice-fieldset">
              <legend class="form-label">历法类型 <span class="required">*</span></legend>
              <div class="choice-grid two">
                <button
                  type="button"
                  class="choice-card horizontal"
                  :class="{ selected: formData.calendarType === 'solar' }"
                  :aria-pressed="formData.calendarType === 'solar'"
                  @click="formData.calendarType = 'solar'"
                >
                  <span>日</span>
                  <div>
                    <strong>公历</strong>
                    <small>身份证日期</small>
                  </div>
                </button>
                <button
                  type="button"
                  class="choice-card horizontal"
                  :class="{ selected: formData.calendarType === 'lunar' }"
                  :aria-pressed="formData.calendarType === 'lunar'"
                  @click="formData.calendarType = 'lunar'"
                >
                  <span>月</span>
                  <div>
                    <strong>农历</strong>
                    <small>传统阴历</small>
                  </div>
                </button>
              </div>
              <p v-if="fieldErrors.calendarType" class="field-error" role="alert">{{ fieldErrors.calendarType }}</p>
            </fieldset>

            <div class="form-group">
              <label class="form-label">出生日期 <span class="required">*</span></label>
              <div class="date-row">
                <label>
                  <input
                    v-model="formData.birthYear"
                    type="tel"
                    inputmode="numeric"
                    placeholder="1990"
                    maxlength="4"
                    @input="validateYear"
                  >
                  <span>年</span>
                </label>
                <label>
                  <input
                    v-model="formData.birthMonth"
                    type="tel"
                    inputmode="numeric"
                    placeholder="01"
                    maxlength="2"
                    @input="validateMonth"
                  >
                  <span>月</span>
                </label>
                <label>
                  <input
                    v-model="formData.birthDay"
                    type="tel"
                    inputmode="numeric"
                    placeholder="01"
                    maxlength="2"
                    @input="validateDay"
                  >
                  <span>日</span>
                </label>
              </div>
              <p v-if="fieldErrors.birth" class="field-error" role="alert">{{ fieldErrors.birth }}</p>
              <p class="form-hint">请按上方选择的历法填写。</p>
            </div>

            <fieldset class="form-group choice-fieldset">
              <legend class="form-label">出生时间 <span class="optional">(选填)</span></legend>
              <div class="choice-grid three">
                <button
                  type="button"
                  class="choice-card compact"
                  :class="{ selected: formData.timeAccuracy === 'unknown' }"
                  :aria-pressed="formData.timeAccuracy === 'unknown'"
                  @click="selectTimeAccuracy('unknown')"
                >
                  不知道
                </button>
                <button
                  type="button"
                  class="choice-card compact"
                  :class="{ selected: formData.timeAccuracy === 'approximate' }"
                  :aria-pressed="formData.timeAccuracy === 'approximate'"
                  @click="selectTimeAccuracy('approximate')"
                >
                  大概时间
                </button>
                <button
                  type="button"
                  class="choice-card compact"
                  :class="{ selected: formData.timeAccuracy === 'exact' }"
                  :aria-pressed="formData.timeAccuracy === 'exact'"
                  @click="selectTimeAccuracy('exact')"
                >
                  精确时间
                </button>
              </div>

              <div v-if="formData.timeAccuracy !== 'unknown'" class="time-row">
                <input
                  v-model="formData.birthHour"
                  type="tel"
                  inputmode="numeric"
                  placeholder="08"
                  maxlength="2"
                  @input="validateHour"
                >
                <span>:</span>
                <input
                  v-model="formData.birthMinute"
                  type="tel"
                  inputmode="numeric"
                  placeholder="30"
                  maxlength="2"
                  @input="validateMinute"
                >
              </div>
            </fieldset>

            <div class="form-group">
              <label class="form-label">出生地 <span class="optional">(选填)</span></label>
              <input
                v-model="formData.birthPlace"
                type="text"
                placeholder="如：北京、上海、广州"
                class="modern-input"
              >
              <p class="form-hint">用于真太阳时校正，提升分析精度。</p>
            </div>

            <button type="button" @click="nextStep" class="primary-button full-width">下一步</button>
            <p v-if="formMessage" id="assessment-step-error" class="form-error" role="alert" aria-live="assertive">{{ formMessage }}</p>
          </form>
        </div>

        <div v-if="currentStep === 2" class="step-content form-panel">
          <div class="step-heading">
            <p class="section-kicker">STEP 02</p>
            <h2 ref="stepHeading" tabindex="-1">选择当下最关注的议题</h2>
            <p>可多选。你提供的真实处境，会帮助说明书回应“我卡在哪”，而不是只讲抽象结论。</p>
          </div>

          <div class="topics-grid">
            <button
              v-for="topic in topics"
              :key="topic.id"
              type="button"
              class="topic-card"
              :class="{ selected: formData.selectedTopics.includes(topic.id) }"
              :aria-pressed="formData.selectedTopics.includes(topic.id)"
              @click="toggleTopic(topic.id)"
            >
              <IconMark :name="topic.icon" />
              <strong>{{ topic.title }}</strong>
              <small>{{ topic.desc }}</small>
            </button>
          </div>

          <div class="form-group">
            <label class="form-label">补充说明 <span class="optional">(选填)</span></label>
            <textarea
              v-model="formData.additionalInfo"
              placeholder="如果有具体问题，可以写在这里。"
              rows="4"
            ></textarea>
          </div>

          <div class="button-row">
            <button type="button" @click="prevStep" class="secondary-button">上一步</button>
            <button type="button" @click="submitAssessment" class="primary-button" :disabled="isSubmitting" :aria-busy="isSubmitting">{{ isSubmitting ? '提交中…' : editingRequestId ? '更新并重新提交' : '提交报告申请' }}</button>
          </div>
          <p v-if="formMessage" id="assessment-step-error" class="form-error" role="alert" aria-live="assertive">{{ formMessage }}</p>
        </div>

        <div v-if="currentStep === 3" class="step-content form-panel">
          <div v-if="isSubmitting" class="generating" role="status" aria-live="polite">
            <div class="loading-compass" aria-hidden="true"></div>
            <h2 ref="stepHeading" tabindex="-1">正在提交你的申请</h2>
            <p>资料正在安全保存。提交完成后，咨询师会在工作台接单并开始准备初步分析。</p>
          </div>

          <div v-else class="result-success">
            <span class="seal-badge">已提交</span>
            <h2 ref="stepHeading" tabindex="-1">申请已收到</h2>
            <p>接下来会经历“咨询师接单—AI 初稿—人工审校—交付”。AI 初稿不会直接展示给你，最终报告交付后会出现在报告列表。</p>
            <div class="application-status paper-card">
              <div><span>申请编号</span><strong>#{{ requestId || '—' }}</strong></div>
              <div><span>当前状态</span><strong>{{ requestStatusLabel }}</strong></div>
            </div>
            <div class="button-row">
              <button type="button" class="primary-button" @click="viewRequests">查看我的申请</button>
              <button type="button" class="secondary-button" @click="goToCalendar">了解决策日历</button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <BrandFooter />
  </div>
</template>

<script>
import { getCurrentUser } from '../utils/authService'
import {
  createServiceRequest,
  getMyServiceRequest,
  resubmitServiceRequest,
  updateServiceRequest
} from '../utils/serviceRequestService'

export default {
  name: 'Assessment',
  data() {
    return {
      currentStep: 1,
      isSubmitting: false,
      formMessage: '',
      fieldErrors: {
        gender: '',
        calendarType: '',
        birth: ''
      },
      requestId: null,
      requestStatus: 'submitted',
      editingRequestId: null,
      idempotencyKey: null,
      formData: {
        gender: '',
        birthYear: '',
        birthMonth: '',
        birthDay: '',
        birthHour: '',
        birthMinute: '',
        birthPlace: '',
        timeAccuracy: 'unknown',
        calendarType: 'solar',
        selectedTopics: [],
        additionalInfo: ''
      },
      years: Array.from({ length: 127 }, (_, i) => 2026 - i),
      topics: [
        { id: 'career', icon: 'career', title: '职业发展', desc: '职业选择、转型、瓶颈突破' },
        { id: 'relationship', icon: 'relationship', title: '亲密关系', desc: '恋爱、婚姻、关系模式' },
        { id: 'family', icon: 'family', title: '家庭议题', desc: '原生家庭、亲子关系' },
        { id: 'self', icon: 'self', title: '自我价值', desc: '自我认同、人生意义' },
        { id: 'growth', icon: 'growth', title: '个人成长', desc: '突破局限、能力提升' },
        { id: 'stress', icon: 'stress', title: '压力焦虑', desc: '情绪管理、压力应对' }
      ],
      currentUser: null
    }
  },
  computed: {
    requestStatusLabel() {
      return {
        submitted: '等待咨询师接单',
        accepted: '咨询师已接单',
        needs_info: '需要补充资料'
      }[this.requestStatus] || '等待咨询师处理'
    }
  },
  async mounted() {
    await this.loadInitialData()
  },
  methods: {
    async loadInitialData() {
      try {
        const user = await getCurrentUser()
        this.currentUser = user
        this.applyUserProfile(user)
        const requestId = this.$route.query.requestId ? Number(this.$route.query.requestId) : null
        if (requestId) {
          const serviceRequest = await getMyServiceRequest(requestId)
          if (serviceRequest.service_type !== 'report' || serviceRequest.status !== 'needs_info') {
            this.formMessage = '这份申请当前不需要补充资料。'
          } else {
            this.editingRequestId = requestId
            this.requestId = requestId
            this.requestStatus = serviceRequest.status
            this.applyRequestPayload(serviceRequest.request_payload)
          }
        }
      } catch (error) {
        this.formMessage = this.errorText(error)
      }
    },
    applyUserProfile(user) {
      this.formData.gender = user.gender || this.formData.gender
      this.formData.birthYear = user.birth_year || this.formData.birthYear
      this.formData.birthMonth = user.birth_month || this.formData.birthMonth
      this.formData.birthDay = user.birth_day || this.formData.birthDay
      this.formData.birthHour = user.birth_hour ?? this.formData.birthHour
      this.formData.birthMinute = user.birth_minute ?? this.formData.birthMinute
      this.formData.birthPlace = user.birth_place || this.formData.birthPlace
      if (user.birth_hour !== null && user.birth_hour !== undefined) this.formData.timeAccuracy = 'approximate'
    },
    applyRequestPayload(payload = {}) {
      const profile = payload.profile || {}
      this.formData = {
        ...this.formData,
        birthYear: profile.birth_year || '',
        birthMonth: profile.birth_month || '',
        birthDay: profile.birth_day || '',
        birthHour: profile.birth_hour ?? '',
        birthMinute: profile.birth_minute ?? '',
        birthPlace: profile.birth_place || '',
        gender: profile.gender || '',
        calendarType: profile.calendar_type || 'solar',
        timeAccuracy: profile.time_accuracy || 'unknown',
        selectedTopics: payload.selected_topics || [],
        additionalInfo: payload.additional_info || ''
      }
    },
    nextStep() {
      this.formMessage = ''
      if (!this.validateStep1()) {
        this.formMessage = '请补充性别和完整出生日期后继续。'
        return
      }
      this.currentStep = 2
      this.focusStepHeading()
    },
    prevStep() {
      this.currentStep = 1
      this.focusStepHeading()
    },
    focusStepHeading() {
      this.$nextTick(() => {
        const ref = this.$refs.stepHeading
        const heading = Array.isArray(ref) ? ref[0] : ref
        if (!heading) return
        window.scrollTo({ top: 0, behavior: 'auto' })
        heading.focus({ preventScroll: true })
      })
    },
    validateStep1() {
      const { gender, birthYear, birthMonth, birthDay, calendarType } = this.formData
      const errors = { gender: '', calendarType: '', birth: '' }
      if (!gender) errors.gender = '请选择性别'
      if (!calendarType) errors.calendarType = '请选择历法类型'
      if (!birthYear || !birthMonth || !birthDay) errors.birth = '请填写完整出生日期'
      if (Object.values(errors).some(Boolean)) {
        this.fieldErrors = errors
        return false
      }

      const year = Number(birthYear)
      const month = Number(birthMonth)
      const day = Number(birthDay)
      if (year < 1900 || year > 2026 || month < 1 || month > 12 || day < 1 || day > 31) {
        this.fieldErrors = { ...errors, birth: '出生日期格式不正确' }
        return false
      }

      if (calendarType === 'solar') {
        const date = new Date(year, month - 1, day)
        const valid = date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day
        this.fieldErrors = valid ? errors : { ...errors, birth: '出生日期不存在' }
        return valid
      }

      const valid = day <= 30
      this.fieldErrors = valid ? errors : { ...errors, birth: '农历日期不能超过 30 日' }
      return valid
    },
    selectTimeAccuracy(accuracy) {
      this.formData.timeAccuracy = accuracy
      if (accuracy === 'unknown') {
        this.formData.birthHour = ''
        this.formData.birthMinute = ''
      }
    },
    validateYear(e) {
      let value = e.target.value.replace(/[^\d]/g, '')
      if (value.length === 4) {
        const num = parseInt(value)
        if (num < 1900) value = '1900'
        if (num > 2026) value = '2026'
      }
      this.formData.birthYear = value
    },
    validateMonth(e) {
      let value = e.target.value.replace(/[^\d]/g, '')
      if (value) {
        const num = parseInt(value)
        if (num > 12) value = '12'
        if (num < 1 && value.length === 2) value = '01'
      }
      this.formData.birthMonth = value
    },
    validateDay(e) {
      let value = e.target.value.replace(/[^\d]/g, '')
      if (value) {
        const num = parseInt(value)
        if (num > 31) value = '31'
        if (num < 1 && value.length === 2) value = '01'
      }
      this.formData.birthDay = value
    },
    validateHour(e) {
      let value = e.target.value.replace(/[^\d]/g, '')
      if (value) {
        const num = parseInt(value)
        if (num > 23) value = '23'
        if (num < 0) value = '0'
      }
      this.formData.birthHour = value
    },
    validateMinute(e) {
      let value = e.target.value.replace(/[^\d]/g, '')
      if (value) {
        const num = parseInt(value)
        if (num > 59) value = '59'
        if (num < 0) value = '0'
      }
      this.formData.birthMinute = value
    },
    toggleTopic(topicId) {
      const index = this.formData.selectedTopics.indexOf(topicId)
      if (index > -1) {
        this.formData.selectedTopics.splice(index, 1)
      } else {
        this.formData.selectedTopics.push(topicId)
      }
    },
    async submitAssessment() {
      this.formMessage = ''
      if (this.isSubmitting) return
      if (!this.validateStep1()) {
        this.formMessage = '请补充性别和完整出生日期后继续。'
        this.currentStep = 1
        this.focusStepHeading()
        return
      }
      this.currentStep = 3
      this.isSubmitting = true
      this.focusStepHeading()

      try {
        const payload = {
          profile: {
            name: this.currentUser?.name || null,
            gender: this.formData.gender,
            birth_year: Number(this.formData.birthYear),
            birth_month: Number(this.formData.birthMonth),
            birth_day: Number(this.formData.birthDay),
            birth_hour: this.formData.timeAccuracy === 'unknown' ? null : Number(this.formData.birthHour),
            birth_minute: this.formData.timeAccuracy === 'unknown' ? null : Number(this.formData.birthMinute || 0),
            birth_place: this.formData.birthPlace || null,
            calendar_type: this.formData.calendarType,
            time_accuracy: this.formData.timeAccuracy
          },
          selected_topics: this.formData.selectedTopics,
          additional_info: this.formData.additionalInfo || null
        }
        let result
        if (this.editingRequestId) {
          await updateServiceRequest(this.editingRequestId, payload)
          result = await resubmitServiceRequest(this.editingRequestId)
        } else {
          this.idempotencyKey = this.idempotencyKey || `report-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
          result = await createServiceRequest({
            service_type: 'report',
            ...payload,
            idempotency_key: this.idempotencyKey
          })
        }
        this.requestId = result.id
        this.requestStatus = result.status
        this.isSubmitting = false
        this.focusStepHeading()
      } catch (error) {
        console.error('报告申请提交失败:', error)
        this.formMessage = this.errorText(error)
        this.currentStep = 2
        this.isSubmitting = false
        this.focusStepHeading()
      }
    },
    viewRequests() {
      this.$router.push('/pages/requests/requests')
    },
    goToCalendar() {
      this.$router.push('/pages/requests/new?type=calendar')
    },
    errorText(error) {
      return error.response?.data?.detail || '申请提交失败，请检查网络后重试。'
    }
  }
}
</script>

<style scoped>
.page-header {
  padding: 82px 0 58px;
  text-align: center;
}

.header-inner {
  max-width: 760px;
}

.page-header h1 {
  font-size: clamp(40px, 8vw, 72px);
  line-height: 1.08;
}

.page-header p:not(.section-kicker) {
  margin-top: 18px;
  color: var(--ink-soft);
  font-size: 17px;
  line-height: 1.75;
}

.assessment-container {
  max-width: 860px;
}

.progress-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  margin-bottom: 22px;
  padding: 14px;
}

.progress-step {
  display: grid;
  justify-items: center;
  gap: 7px;
  width: 72px;
  min-width: 0;
  color: var(--muted);
}

.progress-step span {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--line);
  border-radius: 50%;
  background: rgba(255, 250, 240, 0.72);
  font-family: "Manrope", sans-serif;
  font-weight: 900;
}

.progress-step p {
  font-size: 12px;
  font-weight: 700;
}

.progress-step.active,
.progress-step.completed {
  color: var(--cinnabar-deep);
}

.progress-step.active span,
.progress-step.completed span {
  border-color: rgba(184, 92, 80, 0.34);
  background: rgba(184, 92, 80, 0.1);
}

.progress-line {
  height: 1px;
  background: var(--line);
}

.progress-line.active {
  background: linear-gradient(90deg, var(--cinnabar), var(--gold));
}

.step-content {
  padding: clamp(22px, 4vw, 38px);
}

.step-heading {
  margin-bottom: 26px;
  text-align: center;
}

.step-heading h2 {
  font-size: clamp(26px, 5vw, 40px);
  line-height: 1.2;
}

.step-heading p:not(.section-kicker) {
  margin-top: 10px;
  color: var(--ink-soft);
  line-height: 1.65;
}

.assessment-form,
.form-group {
  display: grid;
  gap: 14px;
}

.assessment-form {
  gap: 26px;
}

.form-label {
  color: var(--ink);
  font-weight: 800;
}

.required {
  color: var(--cinnabar-deep);
}

.optional,
.form-hint {
  color: var(--muted);
  font-size: 13px;
  font-weight: 500;
}

.form-error {
  margin-top: 12px;
  color: var(--cinnabar-deep);
  font-size: 14px;
  line-height: 1.6;
}

.field-error {
  margin: 0;
  color: var(--cinnabar-deep);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.5;
}

.choice-fieldset {
  min-width: 0;
  border: 0;
  padding: 0;
}

.choice-fieldset > legend {
  width: 100%;
  padding: 0;
}

.choice-grid {
  display: grid;
  gap: 10px;
}

.choice-grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.choice-grid.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.choice-card,
.topic-card {
  border: 1px solid var(--line);
  border-radius: 16px;
  background: rgba(255, 250, 240, 0.64);
  color: var(--ink);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.58);
  transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;
}

.choice-card {
  display: grid;
  min-width: 0;
  width: 100%;
  place-items: center;
  min-height: 88px;
  gap: 8px;
  padding: 14px;
}

.choice-card.horizontal {
  grid-template-columns: auto 1fr;
  place-items: center start;
  text-align: left;
}

.choice-card.horizontal > div {
  min-width: 0;
}

.choice-card.compact {
  min-height: 52px;
  font-weight: 800;
}

.choice-card span {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: rgba(184, 92, 80, 0.09);
  color: var(--cinnabar-deep);
  font-weight: 900;
}

.choice-card small {
  display: block;
  margin-top: 3px;
  color: var(--muted);
}

.choice-card.selected,
.topic-card.selected {
  border-color: rgba(184, 92, 80, 0.52);
  background: rgba(255, 239, 222, 0.84);
  transform: translateY(-1px);
}

.date-row {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) minmax(0, 1fr);
  gap: 10px;
}

.date-row label {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: rgba(255, 250, 240, 0.64);
  padding: 10px 12px;
}

.date-row input {
  width: 100%;
  border: 0;
  background: transparent;
  text-align: center;
  font-family: "Manrope", sans-serif;
  font-size: 18px;
  font-weight: 800;
}

.date-row span {
  color: var(--muted);
  font-size: 13px;
}

.time-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 6px;
}

.time-row input {
  max-width: 100%;
  width: 86px;
  padding: 13px;
  text-align: center;
  font-family: "Manrope", sans-serif;
  font-size: 22px;
  font-weight: 900;
}

.modern-input,
textarea {
  width: 100%;
  padding: 14px 16px;
}

.full-width {
  width: 100%;
}

.topics-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 26px;
}

.topic-card {
  display: grid;
  min-width: 0;
  min-height: 142px;
  align-content: start;
  justify-items: start;
  gap: 8px;
  padding: 18px;
  text-align: left;
}

.topic-card .icon-mark {
  width: 26px;
  height: 26px;
  color: var(--cinnabar-deep);
}

.topic-card strong {
  font-size: 17px;
}

.topic-card small {
  color: var(--ink-soft);
  line-height: 1.5;
}

.button-row {
  display: grid;
  grid-template-columns: 0.8fr 1.2fr;
  gap: 12px;
  margin-top: 24px;
}

.generating,
.result-success {
  text-align: center;
}

.loading-compass {
  position: relative;
  width: 86px;
  height: 86px;
  margin: 0 auto 24px;
  border: 1px solid rgba(184, 92, 80, 0.32);
  border-radius: 50%;
}

.loading-compass::before {
  content: "";
  position: absolute;
  left: 50%;
  top: 12px;
  width: 2px;
  height: 62px;
  border-radius: 999px;
  background: linear-gradient(var(--cinnabar-deep) 0 48%, var(--gold) 49% 100%);
  transform: translateX(-50%);
  animation: spin 1.4s linear infinite;
}

@keyframes spin {
  to {
    transform: translateX(-50%) rotate(360deg);
  }
}

.generating h2,
.result-success h2 {
  margin-bottom: 12px;
  font-size: clamp(25px, 5vw, 38px);
}

.generating p,
.result-success > p {
  color: var(--ink-soft);
  line-height: 1.7;
}

.generating-steps {
  display: grid;
  gap: 10px;
  margin-top: 28px;
  text-align: left;
}

.gen-step {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 13px 16px;
  background: rgba(255, 250, 240, 0.54);
  color: var(--muted);
}

.gen-step.active {
  border-color: rgba(184, 92, 80, 0.34);
  background: rgba(255, 239, 222, 0.74);
  color: var(--ink);
  font-weight: 800;
}

.result-preview {
  display: grid;
  gap: 14px;
  margin: 28px 0;
  padding: 20px;
  text-align: left;
}

.result-preview div {
  display: grid;
  gap: 5px;
}

.result-preview span {
  color: var(--gold-deep);
  font-size: 13px;
  font-weight: 800;
}

.result-preview strong {
  color: var(--ink);
  line-height: 1.55;
}

.application-status {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin: 28px 0;
  padding: 20px;
  text-align: left;
}

.application-status div {
  display: grid;
  gap: 5px;
}

.application-status span {
  color: var(--gold-deep);
  font-size: 13px;
  font-weight: 800;
}

.application-status strong {
  color: var(--ink);
  line-height: 1.55;
}

@media (max-width: 767px) {
  .page-header {
    padding: 38px 0 30px;
  }

  .page-header h1 {
    font-size: clamp(32px, 10vw, 44px);
  }

  .page-header p:not(.section-kicker) {
    font-size: 16px;
  }

  .progress-card {
    gap: 5px;
    margin-bottom: 12px;
    padding: 8px 6px;
    border-radius: 14px;
  }

  .progress-step {
    width: 52px;
  }

  .progress-step p {
    font-size: 10px;
  }

  .choice-grid.three,
  .topics-grid {
    grid-template-columns: 1fr;
  }

  .choice-card.compact {
    min-height: 48px;
  }

  .step-content {
    padding: 16px 12px;
    border-radius: 14px;
  }

  .step-heading {
    margin-bottom: 18px;
  }

  .step-heading h2 {
    font-size: clamp(22px, 7vw, 28px);
  }

  .assessment-form {
    gap: 16px;
  }

  .assessment-section {
    padding-top: 30px;
    padding-bottom: 40px;
  }

  .form-group {
    gap: 7px;
  }

  .form-label {
    font-size: 14px;
  }

  .choice-grid,
  .topics-grid {
    gap: 9px;
  }

  .choice-card {
    min-height: 64px;
    padding: 9px;
    border-radius: 12px;
  }

  .choice-card.compact {
    min-height: 46px;
  }

  .choice-card span {
    width: 30px;
    height: 30px;
  }

  .topic-card {
    min-height: 88px;
    gap: 6px;
    padding: 12px;
    border-radius: 12px;
  }

  .topic-card .icon-mark {
    width: 22px;
    height: 22px;
  }

  .topic-card strong {
    font-size: 16px;
  }

  .date-row {
    gap: 6px;
  }

  .date-row label {
    padding: 8px 6px;
    border-radius: 12px;
  }

  .modern-input,
  textarea,
  .date-row input,
  .time-row input {
    min-height: 46px;
    font-size: 16px;
  }

  .button-row {
    gap: 8px;
    margin-top: 16px;
    grid-template-columns: 1fr;
  }

  .button-row .primary-button,
  .button-row .secondary-button,
  .assessment-form > .primary-button {
    min-height: 46px;
  }

  .loading-compass {
    width: 68px;
    height: 68px;
    margin-bottom: 18px;
  }

  .loading-compass::before {
    height: 50px;
  }

  .generating h2,
  .result-success h2 {
    font-size: clamp(23px, 7vw, 30px);
  }

  .generating-steps {
    gap: 8px;
    margin-top: 20px;
  }

  .result-preview {
    gap: 11px;
    margin: 20px 0;
    padding: 14px;
    border-radius: 12px;
  }

  .application-status {
    gap: 11px;
    margin: 20px 0;
    padding: 14px;
    border-radius: 12px;
  }
}

/* 按钮专项：选择项是可点击卡片，流程 CTA 使用一致的左右留白和触控高度。 */
.choice-card,
.topic-card {
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.button-row {
  align-items: stretch;
  gap: var(--button-gap, 8px);
}

.button-row > .primary-button,
.button-row > .secondary-button,
.assessment-form > .primary-button {
  width: 100%;
  min-height: var(--button-height, 46px);
}

</style>
